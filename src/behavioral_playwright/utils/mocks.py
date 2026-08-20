"""
Mock browser, page, mouse, keyboard, and element implementations with lightweight deterministic DOM selector engine.
"""

import html.parser
import re
from typing import Any, Dict, List, Optional, Tuple

from .protocols import ElementHandleProtocol, PageProtocol


class MockDOMNode:
    """Represents a lightweight in-memory DOM element node."""

    def __init__(self, tag: str, attrs: Dict[str, str], parent: Optional["MockDOMNode"] = None) -> None:
        self.tag = tag.lower()
        self.attrs = {k.lower(): v for k, v in attrs.items()}
        self.parent = parent
        self.children: List["MockDOMNode"] = []
        self.text_content: str = ""
        self.x: float = 100.0
        self.y: float = 150.0
        self.width: float = 80.0
        self.height: float = 30.0

    @property
    def id(self) -> str:
        return self.attrs.get("id", "")

    @property
    def classes(self) -> List[str]:
        return self.attrs.get("class", "").split()


class _HTMLDOMBuilder(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.root = MockDOMNode("root", {})
        self.current = self.root

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        attr_dict = {k: (v if v is not None else "") for k, v in attrs}
        node = MockDOMNode(tag, attr_dict, self.current)
        self.current.children.append(node)
        self.current = node

    def handle_endtag(self, tag: str) -> None:
        if self.current.parent is not None:
            self.current = self.current.parent

    def handle_data(self, data: str) -> None:
        self.current.text_content += data


class CSSSelectorMatcher:
    """Lightweight deterministic CSS selector evaluator supporting IDs, classes, attributes, pseudo-classes, and combinators."""

    @classmethod
    def match_all(cls, root: MockDOMNode, selector_string: str) -> List[MockDOMNode]:
        all_nodes = cls._get_all_descendants(root)
        selectors = cls._split_selector_list(selector_string)
        matched: List[MockDOMNode] = []

        for node in all_nodes:
            if any(cls._matches_complex_selector(node, s) for s in selectors):
                if node not in matched:
                    matched.append(node)
        return matched

    @classmethod
    def _get_all_descendants(cls, root: MockDOMNode) -> List[MockDOMNode]:
        nodes: List[MockDOMNode] = []
        for child in root.children:
            nodes.append(child)
            nodes.extend(cls._get_all_descendants(child))
        return nodes

    @classmethod
    def _split_selector_list(cls, selector_string: str) -> List[str]:
        parts: List[str] = []
        current: List[str] = []
        depth_bracket = 0
        depth_paren = 0

        for char in selector_string:
            if char == "[" and depth_paren == 0:
                depth_bracket += 1
            elif char == "]" and depth_paren == 0:
                depth_bracket = max(0, depth_bracket - 1)
            elif char == "(":
                depth_paren += 1
            elif char == ")":
                depth_paren = max(0, depth_paren - 1)
            elif char == "," and depth_bracket == 0 and depth_paren == 0:
                parts.append("".join(current).strip())
                current = []
                continue
            current.append(char)

        if current:
            parts.append("".join(current).strip())
        return [p for p in parts if p]

    @classmethod
    def _matches_complex_selector(cls, node: MockDOMNode, selector: str) -> bool:
        # Tokenize combinators (>, +, ~, or whitespace)
        tokens = cls._tokenize_combinators(selector)
        if not tokens:
            return False

        # Match from right to left
        last_combinator, last_compound = tokens[-1]
        if not cls._matches_compound(node, last_compound):
            return False

        curr_node: Optional[MockDOMNode] = node
        for i in range(len(tokens) - 2, -1, -1):
            if not curr_node:
                return False
            comb, compound = tokens[i + 1][0], tokens[i][1]
            if comb == ">":
                curr_node = curr_node.parent if curr_node.parent else None
                if not curr_node or not cls._matches_compound(curr_node, compound):
                    return False
            elif comb == " ":
                matched_ancestor = False
                parent = curr_node.parent
                while parent and parent.tag != "root":
                    if cls._matches_compound(parent, compound):
                        curr_node = parent
                        matched_ancestor = True
                        break
                    parent = parent.parent
                if not matched_ancestor:
                    return False
            elif comb == "+":
                if not curr_node.parent:
                    return False
                siblings = curr_node.parent.children
                idx = siblings.index(curr_node)
                if idx <= 0 or not cls._matches_compound(siblings[idx - 1], compound):
                    return False
                curr_node = siblings[idx - 1]
            elif comb == "~":
                if not curr_node.parent:
                    return False
                siblings = curr_node.parent.children
                idx = siblings.index(curr_node)
                matched_sibling = False
                for prev in siblings[:idx]:
                    if cls._matches_compound(prev, compound):
                        curr_node = prev
                        matched_sibling = True
                        break
                if not matched_sibling:
                    return False
        return True

    @classmethod
    def _tokenize_combinators(cls, selector: str) -> List[Tuple[str, str]]:
        # Returns list of (combinator_to_prev, compound_selector)
        tokens: List[Tuple[str, str]] = []
        raw_parts = re.split(r"(\s*>\s*|\s*\+\s*|\s*~\s*|\s+)", selector.strip())
        current_comb = ""

        for part in raw_parts:
            if not part:
                continue
            stripped = part.strip()
            if stripped in (">", "+", "~"):
                current_comb = stripped
            elif not stripped:
                current_comb = " "
            else:
                tokens.append((current_comb or " ", stripped))
                current_comb = ""
        return tokens

    @classmethod
    def _matches_compound(cls, node: MockDOMNode, compound: str) -> bool:
        if not compound or compound == "*":
            return True

        # Extract tag
        tag_match = re.match(r"^([a-zA-Z0-9_-]+|\*)", compound)
        tag = tag_match.group(1) if tag_match else ""
        if tag and tag != "*" and node.tag != tag.lower():
            return False

        rest = compound[len(tag) :] if tag else compound

        # Extract IDs
        for id_match in re.findall(r"#([a-zA-Z0-9_-]+)", rest):
            if node.id != id_match:
                return False

        # Extract classes
        for class_match in re.findall(r"\.([a-zA-Z0-9_-]+)", rest):
            if class_match not in node.classes:
                return False

        # Extract attributes: [attr], [attr=val], [attr^=val], [attr$=val], [attr*=val]
        attr_patterns = re.findall(r"\[([a-zA-Z0-9_-]+)(?:([*^$]?=)(?:['\"]?([^'\"\]]+)['\"]?))?\]", rest)
        for attr_name, op, val in attr_patterns:
            attr_name = attr_name.lower()
            if attr_name not in node.attrs:
                return False
            actual_val = node.attrs[attr_name]
            if op == "=" and actual_val != val:
                return False
            elif op == "^=" and not actual_val.startswith(val):
                return False
            elif op == "$=" and not actual_val.endswith(val):
                return False
            elif op == "*=" and val not in actual_val:
                return False

        # Extract pseudo-classes
        pseudo_patterns = re.findall(r":([a-zA-Z0-9_-]+)(?:\(([^)]+)\))?", rest)
        for pseudo, arg in pseudo_patterns:
            pseudo = pseudo.lower()
            if pseudo == "first-child":
                if not node.parent or not node.parent.children or node.parent.children[0] is not node:
                    return False
            elif pseudo == "last-child":
                if not node.parent or not node.parent.children or node.parent.children[-1] is not node:
                    return False
            elif pseudo == "only-child":
                if not node.parent or len(node.parent.children) != 1:
                    return False
            elif pseudo == "nth-child":
                if not node.parent:
                    return False
                idx = node.parent.children.index(node) + 1  # 1-indexed
                if arg.isdigit():
                    if idx != int(arg):
                        return False
                elif arg == "odd" and idx % 2 == 0:
                    return False
                elif arg == "even" and idx % 2 != 0:
                    return False
            elif pseudo == "disabled":
                if "disabled" not in node.attrs:
                    return False
            elif pseudo == "enabled":
                if "disabled" in node.attrs:
                    return False
            elif pseudo == "checked":
                if "checked" not in node.attrs:
                    return False
            elif pseudo == "not":
                if arg and cls._matches_compound(node, arg):
                    return False
            elif pseudo == "has":
                if arg and not cls.match_all(node, arg):
                    return False

        return True


class MockMouse:
    def __init__(self) -> None:
        self.moves: List[Tuple[float, float]] = []
        self.clicks: List[str] = []
        self.wheels: List[Tuple[float, float]] = []

    async def move(self, x: float, y: float) -> None:
        self.moves.append((x, y))

    async def down(self) -> None:
        self.clicks.append("down")

    async def up(self) -> None:
        self.clicks.append("up")

    async def wheel(self, delta_x: float, delta_y: float) -> None:
        self.wheels.append((delta_x, delta_y))


class MockKeyboard:
    def __init__(self) -> None:
        self.keystrokes: List[str] = []

    async def type(self, text: str, delay: Optional[float] = None) -> None:
        for char in text:
            self.keystrokes.append(char)

    async def press(self, key: str) -> None:
        self.keystrokes.append(key)

    def reconstruct_typed_output(self) -> str:
        output: List[str] = []
        for strike in self.keystrokes:
            if strike == "Backspace":
                if output:
                    output.pop()
            else:
                output.append(strike)
        return "".join(output)


class MockElement:
    def __init__(
        self,
        x: float = 100.0,
        y: float = 150.0,
        width: float = 80.0,
        height: float = 30.0,
        node: Optional[MockDOMNode] = None,
    ) -> None:
        self._box = {"x": x, "y": y, "width": width, "height": height}
        self.node = node

    async def bounding_box(self) -> Optional[Dict[str, float]]:
        return self._box


class MockPage:
    DEFAULT_HTML = (
        "<html><body>"
        "<div id='btn-login' class='btn login-btn' role='button'>Login</div>"
        "<input id='text-input' name='login' role='textbox' placeholder='Username'>"
        "<button type='submit' class='submit-btn' disabled>Submit</button>"
        "<a href='/home' class='nav-link'>Home</a>"
        "<div id='test-input' class='interactive'>Test Input</div>"
        "<div id='broken-selector-dynamic' role='button'>Dynamic</div>"
        "<input id='username-broken' name='username'>"
        "<ul class='items'><li>Item 1</li><li>Item 2</li><li>Item 3</li></ul>"
        "Mocked DOM Content"
        "</body></html>"
    )

    def __init__(self, initial_html: Optional[str] = None) -> None:
        self._mouse = MockMouse()
        self._keyboard = MockKeyboard()
        self.navigated_url: Optional[str] = "https://bot-detector.rebrowser.net"
        self.should_fail_goto: bool = False
        self._html: str = initial_html or self.DEFAULT_HTML
        self._dom_tree: MockDOMNode = self._parse_html(self._html)

    def _parse_html(self, html_content: str) -> MockDOMNode:
        builder = _HTMLDOMBuilder()
        builder.feed(html_content)
        return builder.root

    def set_content(self, html_content: str) -> None:
        """Dynamically sets mock page HTML content and updates DOM tree."""
        self._html = html_content
        self._dom_tree = self._parse_html(html_content)

    @property
    def url(self) -> str:
        return self.navigated_url or "https://bot-detector.rebrowser.net"

    @property
    def mouse(self) -> MockMouse:
        return self._mouse

    @property
    def keyboard(self) -> MockKeyboard:
        return self._keyboard

    def _query_selector_all_nodes(self, selector: str) -> List[MockDOMNode]:
        return CSSSelectorMatcher.match_all(self._dom_tree, selector)

    async def evaluate(self, script: str, *args: Any) -> Any:
        if "document.body.innerHTML" in script:
            return self._html

        if "document.querySelectorAll" in script:
            # Extract query from script or use standard interactive selector
            match = re.search(r"querySelectorAll\(\s*['\"]([^'\"]+)['\"]\s*\)", script)
            query = match.group(1) if match else 'button, input, a, [role="button"], [role="link"], [onclick]'
            nodes = self._query_selector_all_nodes(query)
            if not nodes:
                nodes = self._query_selector_all_nodes("button, input, a, div")

            return [
                {
                    "selector": f"#{n.id}"
                    if n.id
                    else (f"{n.tag}.{'.'.join(n.classes)}" if n.classes else n.tag),
                    "text": n.text_content.strip(),
                    "role": n.attrs.get("role", ""),
                    "name": n.attrs.get("name", ""),
                    "tag": n.tag,
                }
                for n in nodes
            ]

        if "createTreeWalker" in script:
            return [
                {"text": "Login", "x": 100.0, "y": 150.0, "width": 80.0, "height": 30.0},
                {"text": "Submit", "x": 200.0, "y": 300.0, "width": 100.0, "height": 40.0},
                {"text": "Enter Username", "x": 150.0, "y": 200.0, "width": 200.0, "height": 25.0},
            ]
        return None

    async def wait_for_selector(
        self, selector: str, state: Optional[str] = None, timeout: Optional[float] = None
    ) -> Optional[ElementHandleProtocol]:
        nodes = self._query_selector_all_nodes(selector)
        if nodes:
            n = nodes[0]
            return MockElement(x=n.x, y=n.y, width=n.width, height=n.height, node=n)
        # Fallback for dynamic unparsed test selectors if needed
        return MockElement()

    async def query_selector(self, selector: str) -> Optional[ElementHandleProtocol]:
        nodes = self._query_selector_all_nodes(selector)
        if nodes:
            n = nodes[0]
            return MockElement(x=n.x, y=n.y, width=n.width, height=n.height, node=n)
        return None

    async def query_selector_all(self, selector: str) -> List[ElementHandleProtocol]:
        nodes = self._query_selector_all_nodes(selector)
        return [MockElement(x=n.x, y=n.y, width=n.width, height=n.height, node=n) for n in nodes]

    async def goto(self, url: str, wait_until: Optional[str] = None, timeout: Optional[float] = None) -> Any:
        if self.should_fail_goto:
            raise RuntimeError("Mock Gateway Timeout or Connection Reset.")
        self.navigated_url = url

        class MockResponse:
            @property
            def ok(self) -> bool:
                return True

            @property
            def status(self) -> int:
                return 200

        return MockResponse()

    async def title(self) -> str:
        return "Mock Browser Environment"

    async def screenshot(self, path: Optional[str] = None) -> Any:
        return b"mock_screenshot_data_png"


class MockBrowserContext:
    def __init__(self) -> None:
        self._pages: List[PageProtocol] = [MockPage()]

    @property
    def pages(self) -> List[PageProtocol]:
        return self._pages

    async def new_page(self) -> PageProtocol:
        page = MockPage()
        self._pages.append(page)
        return page

    async def close(self) -> None:
        pass

    async def add_init_script(self, script: str) -> None:
        pass
