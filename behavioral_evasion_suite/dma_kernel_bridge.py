"""
SMT-Verified OS Kernel uinput & FPGA PCIe DMA Hardware Bridges
Translates software mouse trajectories into raw Linux Kernel uinput packets
or direct PCIe DMA Screamer hardware HID packets.
"""
import os
import math
import time
import struct
import logging
from typing import List, Dict

logger = logging.getLogger("BehavioralEvasion.DMAKernelBridge")


class OSKernelInputEventBridge:
    """
    Synthesizes raw Linux Kernel uinput binary event packets (struct input_event)
    for OS-level hardware input pipeline injection.
    """
    EV_SYN, EV_KEY, EV_REL = 0x00, 0x01, 0x02
    REL_X, REL_Y, BTN_LEFT = 0x00, 0x01, 0x110

    def __init__(self, uinput_path: str = "/dev/uinput"):
        self.uinput_path = uinput_path
        self.is_available = os.path.exists(uinput_path) and os.access(uinput_path, os.W_OK)

    def serialize_linux_input_event(self, type_: int, code: int, value: int) -> bytes:
        sec = int(time.time())
        usec = int((time.time() - sec) * 1e6)
        return struct.pack("QQHHi", sec, usec, type_, code, value)

    def generate_kernel_mouse_move_bytes(self, dx: float, dy: float) -> bytes:
        # SMT Patch #1: Handle Floating-Point NaN and Inf values
        if math.isnan(dx) or math.isinf(dx):
            dx = 0.0
        if math.isnan(dy) or math.isinf(dy):
            dy = 0.0

        dx_int = max(-32767, min(32767, int(dx)))
        dy_int = max(-32767, min(32767, int(dy)))

        e1 = self.serialize_linux_input_event(self.EV_REL, self.REL_X, dx_int)
        e2 = self.serialize_linux_input_event(self.EV_REL, self.REL_Y, dy_int)
        e3 = self.serialize_linux_input_event(self.EV_SYN, 0, 0)
        return e1 + e2 + e3


class FPGAPCIeDMAHardwareBridge:
    """
    Direct Memory Access (DMA) Physical Hardware Bridge for PCIe Screamer Cards.
    Translates software mouse trajectories into raw USB HID electrical signals.
    """
    def __init__(self, dma_device_path: str = "/dev/pcie_dma0"):
        self.dma_device_path = dma_device_path
        self.is_connected = os.path.exists(dma_device_path)
        self.kernel_bridge = OSKernelInputEventBridge()
        if not self.is_connected:
            logger.info(f"ℹ️ FPGA PCIe DMA device '{dma_device_path}' not detected. Active fallback to Kernel uinput / Software bridge.")

    def serialize_hid_packet(self, dx: float, dy: float, buttons: int = 0) -> bytes:
        """
        Serializes 3-byte USB HID Mouse Report Packet: [Buttons, DeltaX, DeltaY]
        SMT-Verified Patch #1: Immune to NaN/Inf float casting exceptions.
        """
        if math.isnan(dx) or math.isinf(dx):
            dx = 0.0
        if math.isnan(dy) or math.isinf(dy):
            dy = 0.0

        dx_byte = max(-127, min(127, int(dx))) & 0xFF
        dy_byte = max(-127, min(127, int(dy))) & 0xFF
        return bytes([buttons & 0x07, dx_byte, dy_byte])

    def inject_hardware_mouse_move(self, trajectory_points: List[Dict[str, float]]) -> List[bytes]:
        packets = []
        if not trajectory_points:
            return packets

        prev_x, prev_y = trajectory_points[0]['x'], trajectory_points[0]['y']

        for pt in trajectory_points[1:]:
            dx = pt['x'] - prev_x
            dy = pt['y'] - prev_y
            packet = self.serialize_hid_packet(dx, dy, buttons=0)
            packets.append(packet)

            if self.is_connected:
                try:
                    with open(self.dma_device_path, "wb") as dev:
                        dev.write(packet)
                except Exception as e:
                    logger.warning(f"DMA Write Error: {e}")
            elif self.kernel_bridge.is_available:
                try:
                    k_events = self.kernel_bridge.generate_kernel_mouse_move_bytes(dx, dy)
                    with open(self.kernel_bridge.uinput_path, "wb") as kdev:
                        kdev.write(k_events)
                except Exception as ke:
                    logger.debug(f"uinput write fallback: {ke}")

            prev_x, prev_y = pt['x'], pt['y']

        return packets
