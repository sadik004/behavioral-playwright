import re
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel


class ActionType(str, Enum):
    NAVIGATE = "NAVIGATE"
    CLICK = "CLICK"
    TYPE = "TYPE"
    SCROLL = "SCROLL"
    PAUSE = "PAUSE"
    EXTRACT = "EXTRACT"
    VERIFY_YARD = "VERIFY_YARD"
    SCREENSHOT = "SCREENSHOT"


class BrowserAction(BaseModel):
    def model_dump(self, **kwargs):
        return self.dict(**kwargs) if hasattr(self, "dict") else super().model_dump(**kwargs)

    action: ActionType
    target: Optional[str] = None
    value: Optional[str] = None
    delay_ms: Optional[float] = None
    description: str


class NLPIntentParser:
    URL_REGEX = re.compile(r"https?://[^\s,]+", re.IGNORECASE)
    SCROLL_REGEX = re.compile(r"(?:scroll|swipe)\s*(?:down|up)?\s*(?:by\s*)?(\d+)?\s*(?:px)?", re.IGNORECASE)
    WAIT_REGEX = re.compile(r"(?:wait|pause|sleep)\s*(?:for\s*)?(\d+(?:\.\d+)?)\s*(milliseconds|ms|seconds|secs|sec|s)?\b", re.IGNORECASE)
    CLICK_REGEX = re.compile(r"""(?:click|press|tap|select)\s*(?:on|the)?\s*['"]?([^'",.]+)['"]?""", re.IGNORECASE)
    TYPE_REGEX = re.compile(r"""(?:type|enter|write|input)\s*['"]([^'"]+)['"](?:\s*(?:into|in|to)\s*(?:the)?\s*['"]?([^'",.]+)['"]?)?""", re.IGNORECASE)
    YARD_REGEX = re.compile(r"""(?:verify\s*yard|check\s*yard|satellite\s*verify)\s*(?:at|for)?\s*['"]?([^'"]+)['"]?""", re.IGNORECASE)
    SPLIT_REGEX = re.compile(
        r"\b(?:and\s+then|then|after\s+that)\b"
        r"|\band\s+(?=(?:click|press|tap|select|type|enter|write|input|scroll|swipe|wait|pause|sleep|goto|go\s+to|open|visit|navigate|verify|check|extract|scrape|screenshot)\b)"
        r"|[;\n]",
        re.IGNORECASE,
    )

    @classmethod
    def resolve_selector(cls, natural_target: str) -> str:
        cleaned = natural_target.strip().strip("'\"")
        if cleaned.startswith(("#", ".", "[", "//")):
            return cleaned
        return f"text={cleaned}, button:has-text('{cleaned}'), a:has-text('{cleaned}')"

    def parse(self, natural_language_input: str) -> List[BrowserAction]:
        clauses = self.SPLIT_REGEX.split(natural_language_input)
        actions: List[BrowserAction] = []

        for raw_clause in clauses:
            clause = raw_clause.strip()
            if not clause:
                continue

            yard_match = self.YARD_REGEX.search(clause)
            if yard_match:
                address = yard_match.group(1).strip()
                actions.append(BrowserAction(
                    action=ActionType.VERIFY_YARD,
                    target=address,
                    description=f"Verify physical satellite yard at '{address}'",
                ))
                continue

            url_match = self.URL_REGEX.search(clause)
            if url_match or any(w in clause.lower() for w in ["goto", "go to", "open", "visit", "navigate"]):
                url = url_match.group(0) if url_match else None
                if not url:
                    for p in clause.split():
                        if "." in p and not p.endswith("."):
                            url = f"https://{p}" if not p.startswith("http") else p
                            break
                if url:
                    actions.append(BrowserAction(
                        action=ActionType.NAVIGATE,
                        target=url,
                        description=f"Navigate in stealth session to {url}",
                    ))
                    continue

            type_match = self.TYPE_REGEX.search(clause)
            if type_match:
                text_to_type = type_match.group(1)
                field_target = type_match.group(2) or "input"
                selector = self.resolve_selector(field_target)
                actions.append(BrowserAction(
                    action=ActionType.TYPE,
                    target=selector,
                    value=text_to_type,
                    description=f"Type '{text_to_type}' into {field_target}",
                ))
                continue

            click_match = self.CLICK_REGEX.search(clause)
            if click_match and not any(w in clause.lower() for w in ["type", "input"]):
                target_elem = click_match.group(1).strip()
                selector = self.resolve_selector(target_elem)
                actions.append(BrowserAction(
                    action=ActionType.CLICK,
                    target=selector,
                    description=f"Human biometric click on '{target_elem}'",
                ))
                continue

            scroll_match = self.SCROLL_REGEX.search(clause)
            if scroll_match:
                amount_str = scroll_match.group(1)
                amount = int(amount_str) if amount_str else 600
                if "up" in clause.lower():
                    amount = -amount
                actions.append(BrowserAction(
                    action=ActionType.SCROLL,
                    value=str(amount),
                    description=f"Newtonian inertial scroll by {amount}px",
                ))
                continue

            wait_match = self.WAIT_REGEX.search(clause)
            if wait_match:
                val = float(wait_match.group(1))
                unit = (wait_match.group(2) or "s").lower()
                ms = val if unit in ("ms", "milliseconds") else val * 1000.0
                actions.append(BrowserAction(
                    action=ActionType.PAUSE,
                    delay_ms=ms,
                    description=f"Cognitive reading pause for {ms:.0f}ms",
                ))
                continue

            if any(w in clause.lower() for w in ["extract", "scrape", "get text", "read"]):
                actions.append(BrowserAction(
                    action=ActionType.EXTRACT,
                    target=clause,
                    description="Extract visible DOM text and headings",
                ))
            elif "screenshot" in clause.lower():
                actions.append(BrowserAction(
                    action=ActionType.SCREENSHOT,
                    description="Capture viewport screenshot",
                ))

        return actions


if __name__ == "__main__":
    p = NLPIntentParser()
    res = p.parse("Go to https://example.com and then wait 2s and then click 'Login' and type 'user' into 'Username'")
    print(f"Parsed {len(res)} actions successfully!")
    for r in res:
        print(f"  [{r.action.value}] {r.description}")
