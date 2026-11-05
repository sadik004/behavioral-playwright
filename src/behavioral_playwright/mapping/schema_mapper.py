"""Structured page understanding and schema mapping engine."""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple, Type, Union
from urllib.parse import urlparse

from behavioral_playwright.exceptions import AmbiguityError, ExtractionError, MappingError
from behavioral_playwright.extraction.dom import (
    extract_json_ld,
    extract_next_data,
    extract_nuxt_data,
    extract_open_graph,
)
from behavioral_playwright.extraction.normalizer import (
    clean_text,
    normalize_whitespace,
    parse_numeric,
    parse_price,
    resolve_url,
)
from behavioral_playwright.logging import get_logger
from behavioral_playwright.mapping.models import (
    FieldEvidence,
    MappedField,
    MappingResult,
    SourceType,
)

logger = get_logger("mapping.schema_mapper")


def _get_raw_page(page: Any) -> Any:
    if hasattr(page, "__class__") and "Mock" in page.__class__.__name__:
        return page
    if hasattr(page, "raw_page") and getattr(page, "raw_page", None) is not None:
        return getattr(page, "raw_page")
    return page


def _current_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class PageSchemaMapper:
    """
    Structured page intelligence and semantic schema mapping engine.
    Extracts candidate evidence across DOM, JSON-LD, OpenGraph, and framework state,
    evaluates confidence, resolves ambiguities, and binds to declared target schemas.
    """

    DEFAULT_PRECEDENCE = [
        SourceType.DOM,
        SourceType.JSON_LD,
        SourceType.OPEN_GRAPH,
        SourceType.NEXT_DATA,
        SourceType.NUXT_DATA,
    ]

    def __init__(
        self,
        confidence_threshold: float = 0.60,
        precedence: Optional[List[SourceType]] = None,
        ambiguity_margin: float = 0.08,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.precedence = precedence or list(self.DEFAULT_PRECEDENCE)
        self.ambiguity_margin = ambiguity_margin

    async def map_schema(
        self,
        page: Any,
        schema: Union[Type[Any], Dict[str, Any]],
        strict_ambiguity: bool = False,
        require_all_fields: bool = False,
    ) -> MappingResult:
        """
        Maps live page content to target schema definition.
        schema can be a Pydantic Model class or dictionary mapping field names to types.
        """
        start_time = time.perf_counter()
        raw_page = _get_raw_page(page)

        # 1. Determine active page URL
        page_url = ""
        try:
            if hasattr(raw_page, "url"):
                u = raw_page.url
                page_url = u() if callable(u) else str(u or "")
            elif hasattr(page, "get_url") and callable(page.get_url):
                page_url = await page.get_url()
        except Exception:
            page_url = ""

        # Check for closed page / navigation failure early
        try:
            if hasattr(raw_page, "is_closed") and callable(raw_page.is_closed) and raw_page.is_closed():
                raise MappingError("Cannot map schema on a closed page.")
        except Exception as e:
            if isinstance(e, MappingError):
                raise

        ts = _current_timestamp()

        # 2. Inspect target schema fields and expected types
        fields_spec: Dict[str, Any] = {}
        model_name: Optional[str] = None

        if isinstance(schema, dict):
            fields_spec = dict(schema)
        elif hasattr(schema, "model_fields"):
            # Pydantic v2
            model_name = schema.__name__
            for f_name, f_field in schema.model_fields.items():
                fields_spec[f_name] = f_field.annotation
        elif hasattr(schema, "__annotations__"):
            # Dataclass or typed dict
            model_name = getattr(schema, "__name__", "StructuredSchema")
            fields_spec = dict(schema.__annotations__)
        else:
            raise MappingError(f"Unsupported schema type: {type(schema)}")

        # 3. Gather evidence from structured metadata layers
        json_ld_data: List[Dict[str, Any]] = []
        og_data: Dict[str, str] = {}
        next_data: Optional[Dict[str, Any]] = None
        nuxt_data: Optional[Dict[str, Any]] = None

        try:
            json_ld_data = await extract_json_ld(raw_page)
        except Exception as exc:
            logger.debug(f"JSON-LD extraction skipped during schema mapping: {exc}")

        try:
            og_data = await extract_open_graph(raw_page)
        except Exception as exc:
            logger.debug(f"OpenGraph extraction skipped during schema mapping: {exc}")

        try:
            next_data = await extract_next_data(raw_page)
        except Exception as exc:
            logger.debug(f"Next.js data extraction skipped: {exc}")

        try:
            nuxt_data = await extract_nuxt_data(raw_page)
        except Exception as exc:
            logger.debug(f"Nuxt data extraction skipped: {exc}")

        # 4. Gather live DOM candidate evidence
        dom_evidence = await self._extract_dom_evidence(raw_page, page_url, ts)

        # 5. Map each schema field against all gathered evidence
        mapped_fields: Dict[str, MappedField] = {}
        final_data: Dict[str, Any] = {}
        ambiguities: List[str] = []
        missing_fields: List[str] = []
        conflicts: List[Dict[str, Any]] = []

        total_confidence = 0.0

        for field_name, expected_type in fields_spec.items():
            candidates: List[FieldEvidence] = []

            # 5.1 DOM Candidates
            field_dom_candidates = self._find_dom_candidates(field_name, expected_type, dom_evidence)
            candidates.extend(field_dom_candidates)

            # 5.2 JSON-LD Candidates
            for jld in json_ld_data:
                jld_cand = self._find_metadata_candidate(field_name, jld, SourceType.JSON_LD, page_url, ts)
                if jld_cand:
                    candidates.append(jld_cand)

            # 5.3 OpenGraph Candidates
            og_cand = self._find_og_candidate(field_name, og_data, page_url, ts)
            if og_cand:
                candidates.append(og_cand)

            # 5.4 Framework State Candidates
            if next_data and isinstance(next_data, dict):
                next_cand = self._find_nested_dict_candidate(field_name, next_data, SourceType.NEXT_DATA, page_url, ts)
                if next_cand:
                    candidates.append(next_cand)

            if nuxt_data and isinstance(nuxt_data, dict):
                nuxt_cand = self._find_nested_dict_candidate(field_name, nuxt_data, SourceType.NUXT_DATA, page_url, ts)
                if nuxt_cand:
                    candidates.append(nuxt_cand)

            if not candidates:
                missing_fields.append(field_name)
                continue

            # Sort candidates by:
            # 1. Source precedence rank
            # 2. Confidence score descending
            def _candidate_rank(c: FieldEvidence) -> Tuple[int, float]:
                try:
                    p_idx = self.precedence.index(c.source_type)
                except ValueError:
                    p_idx = 99
                # Negative confidence for descending sort
                return (p_idx, -c.confidence)

            candidates.sort(key=_candidate_rank)

            # Check for ambiguity among candidates in the same precedence tier
            top_cand = candidates[0]
            is_ambiguous = False
            alt_candidates = []

            if len(candidates) > 1:
                second_cand = candidates[1]
                top_tier = self.precedence.index(top_cand.source_type) if top_cand.source_type in self.precedence else 99
                second_tier = self.precedence.index(second_cand.source_type) if second_cand.source_type in self.precedence else 99

                # Intra-tier ambiguity: competing candidates within the same tier (e.g., two DOM elements)
                if top_tier == second_tier:
                    if (
                        top_cand.confidence >= self.confidence_threshold
                        and second_cand.confidence >= self.confidence_threshold
                        and abs(top_cand.confidence - second_cand.confidence) <= self.ambiguity_margin
                        and str(top_cand.normalized_value).strip().lower() != str(second_cand.normalized_value).strip().lower()
                    ):
                        is_ambiguous = True
                        ambiguities.append(field_name)
                        alt_candidates = candidates[1:]
                else:
                    # Cross-tier disagreement: preserve conflict audit trail while applying precedence
                    if str(top_cand.normalized_value).strip().lower() != str(second_cand.normalized_value).strip().lower():
                        conflicts.append({
                            "field": field_name,
                            "chosen_source": top_cand.source_type.value,
                            "chosen_value": top_cand.normalized_value,
                            "competing_source": second_cand.source_type.value,
                            "competing_value": second_cand.normalized_value,
                            "resolution": "RESOLVED_BY_PRECEDENCE",
                        })


            # Check confidence threshold
            if top_cand.confidence < self.confidence_threshold:
                missing_fields.append(field_name)
                continue

            if is_ambiguous and strict_ambiguity:
                raise AmbiguityError(
                    f"Ambiguous candidates for field '{field_name}': "
                    f"'{top_cand.normalized_value}' ({top_cand.confidence:.2f}) vs "
                    f"'{candidates[1].normalized_value}' ({candidates[1].confidence:.2f})"
                )

            # Type normalization and coercion
            coerced_value = self._coerce_type(top_cand.normalized_value, expected_type)
            if coerced_value is None and top_cand.normalized_value is not None:
                conflicts.append({
                    "field": field_name,
                    "expected_type": str(expected_type),
                    "raw_value": top_cand.raw_value,
                    "error": "Type conversion failure"
                })

            final_data[field_name] = coerced_value
            mapped_fields[field_name] = MappedField(
                name=field_name,
                value=coerced_value,
                confidence=top_cand.confidence,
                evidence=top_cand,
                is_ambiguous=is_ambiguous,
                candidate_count=len(candidates),
                alternative_candidates=alt_candidates,
            )
            total_confidence += top_cand.confidence

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        avg_confidence = (total_confidence / len(fields_spec)) if fields_spec else 0.0

        if require_all_fields and missing_fields:
            raise MappingError(f"Required schema fields could not be resolved: {missing_fields}")

        success = (len(missing_fields) == 0 and len(ambiguities) == 0 and len(final_data) > 0)

        return MappingResult(
            success=success,
            model=model_name,
            data=final_data,
            fields=mapped_fields,
            confidence=round(avg_confidence, 4),
            ambiguities=ambiguities,
            missing_fields=missing_fields,
            conflicts=conflicts,
            page_url=page_url,
            timestamp=ts,
            elapsed_ms=round(elapsed_ms, 2),
        )

    async def _extract_dom_evidence(self, raw_page: Any, page_url: str, ts: str) -> List[Dict[str, Any]]:
        """Collects semantic candidate elements from the live DOM."""
        script = """
        () => {
            const results = [];
            const seen = new Set();

            function addCandidate(el, roleHint, scoreBoost) {
                if (!el || seen.has(el)) return;
                seen.add(el);

                const text = (el.innerText || el.textContent || '').trim();
                const tag = el.tagName.toLowerCase();
                const id = el.id || '';
                const className = typeof el.className === 'string' ? el.className : '';
                const itemprop = el.getAttribute('itemprop') || '';
                const testid = el.getAttribute('data-testid') || '';
                const name = el.getAttribute('name') || '';
                const ariaLabel = el.getAttribute('aria-label') || '';
                const role = el.getAttribute('role') || '';
                const src = el.src || el.getAttribute('src') || '';
                const href = el.href || el.getAttribute('href') || '';
                const value = el.value !== undefined ? el.value : '';

                // Build a selector string for provenance
                let sel = tag;
                if (id) sel += '#' + id;
                else if (itemprop) sel += `[itemprop="${itemprop}"]`;
                else if (testid) sel += `[data-testid="${testid}"]`;
                else if (className) sel += '.' + className.split(' ')[0];

                results.push({
                    tag: tag,
                    text: text,
                    value: value,
                    src: src,
                    href: href,
                    id: id,
                    className: className,
                    itemprop: itemprop,
                    testid: testid,
                    name: name,
                    ariaLabel: ariaLabel,
                    role: role,
                    selector: sel,
                    roleHint: roleHint,
                    scoreBoost: scoreBoost
                });
            }

            // 1. Headings (h1, h2, h3)
            document.querySelectorAll('h1, h2, h3').forEach(h => addCandidate(h, 'heading', 0.20));

            // 2. Microdata itemprops
            document.querySelectorAll('[itemprop]').forEach(el => addCandidate(el, 'itemprop', 0.35));

            // 3. Test IDs and Form Controls
            document.querySelectorAll('[data-testid], [role], input, textarea, select').forEach(el => addCandidate(el, 'semantic', 0.25));

            // 4. Elements with price, title, sku, name classes or IDs
            document.querySelectorAll('[id*="price"], [class*="price"], [id*="title"], [class*="title"], [id*="sku"], [class*="sku"], [id*="name"], [class*="name"], [id*="desc"], [class*="desc"]').forEach(el => addCandidate(el, 'keyword', 0.20));

            // 5. Images with alt or itemprop
            document.querySelectorAll('img[src]').forEach(img => addCandidate(img, 'image', 0.15));

            return results.slice(0, 100);
        }
        """
        try:
            raw_res = await raw_page.evaluate(script)
            return raw_res if isinstance(raw_res, list) else []
        except Exception as e:
            logger.debug(f"DOM semantic scan evaluation failed: {e}")
            return []

    def _find_dom_candidates(
        self,
        field_name: str,
        expected_type: Any,
        dom_evidence: List[Dict[str, Any]]
    ) -> List[FieldEvidence]:
        """Matches gathered DOM candidates to a target schema field name."""
        candidates: List[FieldEvidence] = []
        target_norm = field_name.strip().lower()

        is_price_field = any(k in target_norm for k in ("price", "cost", "amount", "rate"))
        is_title_field = any(k in target_norm for k in ("title", "headline", "product_name")) or target_norm == "name"
        is_sku_field = any(k in target_norm for k in ("sku", "code", "barcode", "identifier"))
        is_image_field = any(k in target_norm for k in ("image", "photo", "img", "thumbnail", "picture"))
        is_desc_field = any(k in target_norm for k in ("desc", "description", "summary", "detail"))
        is_stock_field = any(k in target_norm for k in ("stock", "avail", "inventory"))

        for item in dom_evidence:
            confidence = 0.0
            reasons = []

            # 1. Exact Microdata itemprop match (+0.55)
            itemprop_val = item.get("itemprop", "").strip().lower()
            if itemprop_val and (itemprop_val == target_norm or itemprop_val.replace("-", "_") == target_norm.replace("-", "_")):
                confidence += 0.55
                reasons.append("itemprop_exact_match")

            # 2. data-testid exact match (+0.55)
            testid_val = item.get("testid", "").strip().lower()
            if testid_val and (testid_val == target_norm or testid_val.replace("-", "_") == target_norm.replace("-", "_")):
                confidence += 0.55
                reasons.append("testid_exact_match")

            # 3. id or name exact match (+0.45)
            id_val = item.get("id", "").strip().lower()
            if id_val and (id_val == target_norm or id_val.replace("-", "_") == target_norm.replace("-", "_")):
                confidence += 0.45
                reasons.append("id_exact_match")
            name_val = item.get("name", "").strip().lower()
            if name_val and (name_val == target_norm or name_val.replace("-", "_") == target_norm.replace("-", "_")):
                confidence += 0.45
                reasons.append("name_exact_match")

            # 4. Semantic class match (+0.30)
            class_str = item.get("className", "").lower()
            if class_str:
                classes = [c.replace("-", "_") for c in class_str.split()]
                if target_norm.replace("-", "_") in classes or any(target_norm in c for c in classes):
                    confidence += 0.30
                    reasons.append("class_exact_match")

            # 5. Specialized Type / Tag heuristics
            if is_price_field:
                text_val = item.get("text", "")
                if parse_price(text_val) is not None:
                    confidence += 0.35
                    reasons.append("valid_price_format")
                    if "price" in item.get("className", "").lower() or "price" in item.get("id", "").lower():
                        confidence += 0.20
                        reasons.append("price_class_or_id")

            elif is_title_field:
                tag = item.get("tag", "")
                if tag == "h1":
                    confidence += 0.45
                    reasons.append("h1_tag")
                elif tag in ("h2", "h3"):
                    confidence += 0.30
                    reasons.append(f"{tag}_tag")

            elif is_image_field:
                if item.get("tag") == "img" and item.get("src"):
                    confidence += 0.40
                    reasons.append("img_tag")
                    if target_norm in item.get("alt", "").lower() or target_norm in item.get("className", "").lower():
                        confidence += 0.25
                        reasons.append("image_alt_class_match")

            elif is_sku_field:
                if "sku" in item.get("className", "").lower() or "sku" in item.get("id", "").lower():
                    confidence += 0.40
                    reasons.append("sku_context")

            elif is_stock_field:
                text_val = item.get("text", "").lower()
                if any(w in text_val for w in ("in stock", "out of stock", "available", "backorder")):
                    confidence += 0.35
                    reasons.append("stock_text_match")
                if "stock" in item.get("className", "").lower() or "stock" in item.get("id", "").lower():
                    confidence += 0.20
                    reasons.append("stock_class_or_id")

            elif is_desc_field:
                if item.get("tag") == "p" or "desc" in item.get("className", "").lower():
                    confidence += 0.30
                    reasons.append("desc_context")

            # Bound confidence
            confidence = min(round(confidence, 3), 0.98)

            if confidence >= self.confidence_threshold:
                # Determine raw value
                if is_image_field and item.get("src"):
                    raw_val = item["src"]
                elif item.get("value") and item.get("tag") in ("input", "textarea", "select"):
                    raw_val = item["value"]
                else:
                    raw_val = item.get("text", "")

                norm_val = clean_text(str(raw_val)) if raw_val else ""

                candidates.append(FieldEvidence(
                    name=field_name,
                    source_type=SourceType.DOM,
                    raw_value=raw_val,
                    normalized_value=norm_val,
                    confidence=confidence,
                    selector=item.get("selector"),
                    tag=item.get("tag"),
                    attributes={
                        "id": item.get("id"),
                        "class": item.get("className"),
                        "itemprop": item.get("itemprop"),
                        "data-testid": item.get("testid"),
                        "aria-label": item.get("ariaLabel")
                    },
                    reason=", ".join(reasons)
                ))

        return candidates

    def _find_metadata_candidate(
        self,
        field_name: str,
        meta_dict: Dict[str, Any],
        source_type: SourceType,
        page_url: str,
        ts: str
    ) -> Optional[FieldEvidence]:
        """Inspects JSON-LD schema objects for target field matches."""
        target_norm = field_name.strip().lower()

        # Check direct key
        for k, v in meta_dict.items():
            if str(k).strip().lower() == target_norm and v:
                return FieldEvidence(
                    name=field_name,
                    source_type=source_type,
                    raw_value=v,
                    normalized_value=clean_text(str(v)) if isinstance(v, str) else v,
                    confidence=0.92,
                    page_url=page_url,
                    timestamp=ts,
                    reason=f"json_ld_exact_property_{k}"
                )

        # Check nested offers for price
        if any(k in target_norm for k in ("price", "cost")) and "offers" in meta_dict:
            offers = meta_dict["offers"]
            if isinstance(offers, dict) and "price" in offers:
                p_val = offers["price"]
                return FieldEvidence(
                    name=field_name,
                    source_type=source_type,
                    raw_value=p_val,
                    normalized_value=str(p_val),
                    confidence=0.94,
                    page_url=page_url,
                    timestamp=ts,
                    reason="json_ld_offers_price"
                )

        # Check name for title
        if target_norm in ("title", "headline") and "name" in meta_dict:
            return FieldEvidence(
                name=field_name,
                source_type=source_type,
                raw_value=meta_dict["name"],
                normalized_value=clean_text(str(meta_dict["name"])),
                confidence=0.88,
                page_url=page_url,
                timestamp=ts,
                reason="json_ld_name_as_title"
            )

        return None

    def _find_og_candidate(
        self,
        field_name: str,
        og_dict: Dict[str, str],
        page_url: str,
        ts: str
    ) -> Optional[FieldEvidence]:
        """Inspects OpenGraph and Twitter card metadata for target field matches."""
        target_norm = field_name.strip().lower()

        og_mappings = {
            "title": ["og:title", "twitter:title"],
            "name": ["og:title", "twitter:title"],
            "description": ["og:description", "twitter:description"],
            "image": ["og:image", "twitter:image"],
            "url": ["og:url"],
        }

        keys_to_check = og_mappings.get(target_norm, [f"og:{target_norm}", f"twitter:{target_norm}"])
        for k in keys_to_check:
            if k in og_dict and og_dict[k]:
                return FieldEvidence(
                    name=field_name,
                    source_type=SourceType.OPEN_GRAPH,
                    raw_value=og_dict[k],
                    normalized_value=clean_text(og_dict[k]),
                    confidence=0.86,
                    page_url=page_url,
                    timestamp=ts,
                    reason=f"opengraph_property_{k}"
                )
        return None

    def _find_nested_dict_candidate(
        self,
        field_name: str,
        data_dict: Dict[str, Any],
        source_type: SourceType,
        page_url: str,
        ts: str
    ) -> Optional[FieldEvidence]:
        """Walks dictionary looking for matching key."""
        target_norm = field_name.strip().lower()

        def _walk(d: Any) -> Optional[Any]:
            if isinstance(d, dict):
                for k, v in d.items():
                    if str(k).strip().lower() == target_norm:
                        return v
                    res = _walk(v)
                    if res is not None:
                        return res
            elif isinstance(d, list):
                for item in d:
                    res = _walk(item)
                    if res is not None:
                        return res
            return None

        val = _walk(data_dict)
        if val is not None:
            return FieldEvidence(
                name=field_name,
                source_type=source_type,
                raw_value=val,
                normalized_value=clean_text(str(val)) if isinstance(val, str) else val,
                confidence=0.84,
                page_url=page_url,
                timestamp=ts,
                reason=f"framework_state_{source_type.value}"
            )
        return None

    def _coerce_type(self, value: Any, target_type: Any) -> Any:
        """Coerces extracted value into target schema type without silent corruption."""
        if value is None:
            return None

        # Check typing.Optional
        type_str = str(target_type)
        if "Optional[" in type_str or "Union[" in type_str:
            # Extract underlying type if possible
            if hasattr(target_type, "__args__"):
                args = [a for a in target_type.__args__ if a is not type(None)]
                if args:
                    target_type = args[0]

        if target_type in (Decimal, "Decimal"):
            return parse_price(str(value))
        elif target_type in (float, "float"):
            return parse_numeric(str(value))
        elif target_type in (int, "int"):
            num = parse_numeric(str(value))
            return int(num) if num is not None else None
        elif target_type in (bool, "bool"):
            if isinstance(value, bool):
                return value
            s = str(value).strip().lower()
            if s in ("true", "1", "yes", "in stock", "available"):
                return True
            if s in ("false", "0", "no", "out of stock", "unavailable"):
                return False
            return None
        elif target_type in (str, "str"):
            return clean_text(str(value))
        elif target_type in (list, "list", List[str]):
            if isinstance(value, list):
                return [clean_text(str(v)) for v in value]
            return [clean_text(str(value))]

        return value
