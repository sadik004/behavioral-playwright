"""Backward-compatible module forwarding to `veil.kinematics.dom_telemetry`."""

from veil.kinematics.dom_telemetry import (
    DOMEventRecord,
    DOMTelemetryCollector,
    PageTelemetryAuditor,
)

__all__ = [
    "DOMEventRecord",
    "DOMTelemetryCollector",
    "PageTelemetryAuditor",
]
