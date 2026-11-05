"""Pillar 4A: RFC 3986 URL Canonicalizer & 64-Bit Charikar SimHash Deduplicator.

Implements FineWeb / CommonCrawl grade URL normalization and 64-bit Locality-Sensitive
Hashing (SimHash) so near-duplicate pages (sort permutations, tracking parameters,
session IDs, dynamic footer timestamps) are detected in O(1) time.
"""

from __future__ import annotations

import hashlib
import re
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

_TRACKING_PARAMS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "utm_id",
        "fbclid",
        "gclid",
        "msclkid",
        "dclid",
        "twclid",
        "_ga",
        "_gl",
        "mc_cid",
        "mc_eid",
        "ref",
        "ref_src",
        "spm",
        "sessionid",
        "phpsessid",
    }
)


def canonicalize_url(url: str, base_url: Optional[str] = None) -> str:
    """Normalizes URLs per RFC 3986, strips tracking params, and sorts query parameters."""
    resolved = urljoin(base_url, url.strip()) if base_url else url.strip()
    parts = urlsplit(resolved)
    scheme = (parts.scheme or "https").lower()
    netloc = parts.netloc.lower()

    # Remove default ports
    if netloc.endswith(":80") and scheme == "http":
        netloc = netloc[:-3]
    elif netloc.endswith(":443") and scheme == "https":
        netloc = netloc[:-4]

    # Collapse multiple slashes and normalize path
    path = re.sub(r"/+", "/", parts.path or "/")
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    # Filter tracking query parameters and sort alphabetically
    filtered_q = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=False)
        if k.lower() not in _TRACKING_PARAMS and not k.lower().startswith("utm_")
    ]
    filtered_q.sort(key=lambda item: (item[0], item[1]))
    query_str = urlencode(filtered_q, doseq=True)

    # Drop fragment (#...)
    return urlunsplit((scheme, netloc, path, query_str, ""))


def compute_simhash_64(text: str, shingle_size: int = 3) -> int:
    """Computes a 64-bit Charikar SimHash fingerprint over word shingles."""
    tokens = re.findall(r"[a-z0-9ঀ-৿]+", (text or "").lower())
    if not tokens:
        return 0

    if len(tokens) < shingle_size:
        shingles = [" ".join(tokens)]
    else:
        shingles = [
            " ".join(tokens[i : i + shingle_size])
            for i in range(len(tokens) - shingle_size + 1)
        ]

    v = [0] * 64
    for shingle in shingles:
        digest = hashlib.blake2b(shingle.encode("utf-8"), digest_size=8).digest()
        h = int.from_bytes(digest, byteorder="big", signed=False)
        for bit_idx in range(64):
            if (h >> bit_idx) & 1:
                v[bit_idx] += 1
            else:
                v[bit_idx] -= 1

    fingerprint = 0
    for bit_idx in range(64):
        if v[bit_idx] > 0:
            fingerprint |= 1 << bit_idx
    return fingerprint


def hamming_distance_64(hash_a: int, hash_b: int) -> int:
    """Returns the bitwise Hamming distance between two 64-bit integers."""
    return ((hash_a ^ hash_b) & ((1 << 64) - 1)).bit_count()


class SimHashDeduplicator:
    """Maintains a 4-band LSH index over 64-bit SimHashes for fast near-duplicate detection."""

    def __init__(self, max_hamming_distance: int = 3) -> None:
        self.max_hamming_distance = max_hamming_distance
        self._seen_urls: Set[str] = set()
        self._hashes: List[Tuple[int, str]] = []
        self._bands: Dict[Tuple[int, int], List[int]] = {}

    def mark_url_seen(self, url: str, base_url: Optional[str] = None) -> Tuple[bool, str]:
        """Returns `(already_seen, canonical_url)`."""
        canon = canonicalize_url(url, base_url=base_url)
        if canon in self._seen_urls:
            return True, canon
        self._seen_urls.add(canon)
        return False, canon

    def check_and_add_content(
        self,
        text: str,
        url: str = "",
        max_hamming_distance: Optional[int] = None,
    ) -> Tuple[bool, int, int, Optional[str]]:
        """Checks whether `text` is a near-duplicate of any previously indexed page.

        Returns `(is_duplicate, simhash_int, min_hamming_distance, matched_url)`.
        """
        threshold = (
            self.max_hamming_distance
            if max_hamming_distance is None
            else max_hamming_distance
        )
        sh = compute_simhash_64(text)

        # Probe 4x16-bit bands for candidate matches
        candidates: Set[int] = set()
        for band_idx in range(4):
            band_val = (sh >> (band_idx * 16)) & 0xFFFF
            for cand_idx in self._bands.get((band_idx, band_val), ()):
                candidates.add(cand_idx)

        # If threshold > 3 or small index, also check full list to guarantee exact recall
        iterable_indices = (
            candidates if (threshold <= 3 and len(self._hashes) > 64) else range(len(self._hashes))
        )

        min_dist = 65
        matched_url: Optional[str] = None
        for idx in iterable_indices:
            existing_hash, existing_url = self._hashes[idx]
            dist = hamming_distance_64(sh, existing_hash)
            if dist < min_dist:
                min_dist = dist
                matched_url = existing_url
            if dist <= threshold:
                return True, sh, dist, existing_url

        # Index new SimHash
        new_idx = len(self._hashes)
        self._hashes.append((sh, url))
        for band_idx in range(4):
            band_val = (sh >> (band_idx * 16)) & 0xFFFF
            self._bands.setdefault((band_idx, band_val), []).append(new_idx)

        return False, sh, (0 if min_dist == 65 else min_dist), matched_url
