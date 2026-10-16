"""Backward-compatible module forwarding to `veil.kinematics.kernel_input_bridge`."""

from veil.kinematics.kernel_input_bridge import (
    WindowsKernelInputEventBridge,
    OSKernelInputEventBridge,
    FPGAPCIeDMAHardwareBridge,
    KernelInputBridge,
)

__all__ = [
    "WindowsKernelInputEventBridge",
    "OSKernelInputEventBridge",
    "FPGAPCIeDMAHardwareBridge",
    "KernelInputBridge",
]
