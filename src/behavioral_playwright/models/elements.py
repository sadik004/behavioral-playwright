"""DOM element representations for behavioral-playwright."""

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class BoundingBox:
    """Represents the screen-space bounding box of an element."""
    x: float
    y: float
    width: float
    height: float

    @property
    def center_x(self) -> float:
        return self.x + (self.width / 2.0)

    @property
    def center_y(self) -> float:
        return self.y + (self.height / 2.0)


@dataclass
class DOMElement:
    """Represents a lightweight, observable DOM element representation."""
    tag: str
    id: str = ""
    class_name: str = ""
    text: str = ""
    role: str = ""
    aria_label: str = ""
    placeholder: str = ""
    name: str = ""
    title: str = ""
    alt: str = ""
    href: str = ""
    selector: str = ""
    is_visible: bool = True
    attributes: Dict[str, str] = field(default_factory=dict)
    bounding_box: Optional[BoundingBox] = None

    def get_accessible_name(self) -> str:
        """Returns the best candidate for the accessible name."""
        return (
            self.aria_label
            or self.text
            or self.placeholder
            or self.title
            or self.alt
            or self.name
        ).strip()
