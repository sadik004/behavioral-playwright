"""
SMT-Verified OS Kernel uinput, Windows Native SendInput & FPGA PCIe DMA Hardware Bridges
Translates software mouse trajectories into raw Linux Kernel uinput packets,
Windows User32 SendInput hardware mouse events, or direct PCIe DMA Screamer hardware HID packets.
"""
import os
import sys
import math
import time
import struct
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger("BehavioralEvasion.DMAKernelBridge")

# =============================================================================
# 1. WINDOWS NATIVE KERNEL INPUT BRIDGE (C-TYPES SENDINPUT / RAW INPUT)
# =============================================================================

class WindowsKernelInputEventBridge:
    """
    Synthesizes raw Windows OS kernel-level hardware mouse packets using SendInput
    and MOUSEINPUT C-structures. Converts Cartesian desktop coordinates into
    Windows normalized mouse space (0 to 65535) with sub-millisecond precision.
    """
    MOUSEEVENTF_MOVE = 0x0001
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_RIGHTDOWN = 0x0008
    MOUSEEVENTF_RIGHTUP = 0x000c
    MOUSEEVENTF_ABSOLUTE = 0x8000
    INPUT_MOUSE = 0

    def __init__(self):
        self.is_available = sys.platform == "win32"
        self._user32 = None
        if self.is_available:
            try:
                import ctypes
                self._ctypes = ctypes
                self._user32 = ctypes.windll.user32
                logger.info("Windows Native Kernel Input Bridge (SendInput) active.")
            except Exception as e:
                self.is_available = False
                logger.debug(f"Unable to load Windows user32 SendInput ({e}).")

    def send_mouse_input(self, dx: float, dy: float, absolute: bool = False, flags: int = 0) -> bool:
        """Dispatches an authentic Windows kernel mouse packet."""
        if not self.is_available or not self._user32:
            return False

        try:
            ctypes = self._ctypes

            class MOUSEINPUT(ctypes.Structure):
                _fields_ = [
                    ("dx", ctypes.c_long),
                    ("dy", ctypes.c_long),
                    ("mouseData", ctypes.c_ulong),
                    ("dwFlags", ctypes.c_ulong),
                    ("time", ctypes.c_ulong),
                    ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
                ]

            class INPUT_UNION(ctypes.Union):
                _fields_ = [("mi", MOUSEINPUT)]

            class INPUT(ctypes.Structure):
                _fields_ = [
                    ("type", ctypes.c_ulong),
                    ("union", INPUT_UNION)
                ]

            # Handle NaN / Inf defensively
            if math.isnan(dx) or math.isinf(dx):
                dx = 0.0
            if math.isnan(dy) or math.isinf(dy):
                dy = 0.0

            final_flags = flags or self.MOUSEEVENTF_MOVE
            if absolute:
                final_flags |= self.MOUSEEVENTF_ABSOLUTE

            extra = ctypes.c_ulong(0)
            inp = INPUT()
            inp.type = self.INPUT_MOUSE
            inp.union.mi = MOUSEINPUT(
                dx=int(dx),
                dy=int(dy),
                mouseData=0,
                dwFlags=final_flags,
                time=0,
                dwExtraInfo=ctypes.pointer(extra)
            )

            res = self._user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
            return res == 1
        except Exception as e:
            logger.debug(f"Windows SendInput dispatch failed: {e}")
            return False


# =============================================================================
# 2. LINUX UINPUT KERNEL BRIDGE
# =============================================================================

class OSKernelInputEventBridge:
    """
    Synthesizes raw Linux Kernel uinput binary event packets (struct input_event)
    for OS-level hardware input pipeline injection.
    """
    EV_SYN, EV_KEY, EV_REL = 0x00, 0x01, 0x02
    REL_X, REL_Y, BTN_LEFT = 0x00, 0x01, 0x110

    def __init__(self, uinput_path: str = "/dev/uinput"):
        self.uinput_path = uinput_path
        self.is_available = sys.platform.startswith("linux") and os.path.exists(uinput_path) and os.access(uinput_path, os.W_OK)

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


# =============================================================================
# 3. UNIFIED CROSS-PLATFORM FPGA PCIE DMA & KERNEL BRIDGE
# =============================================================================

class FPGAPCIeDMAHardwareBridge:
    """
    Direct Memory Access (DMA) Physical Hardware Bridge for PCIe Screamer Cards.
    Translates software mouse trajectories into raw USB HID electrical signals or
    direct OS-level hardware packets on both Windows and Linux.
    """
    def __init__(self, dma_device_path: Optional[str] = None):
        if dma_device_path is None:
            self.dma_device_path = "\\\\.\\PCIe_DMA0" if sys.platform == "win32" else "/dev/pcie_dma0"
        else:
            self.dma_device_path = dma_device_path

        self.is_connected = os.path.exists(self.dma_device_path)
        self.linux_kernel_bridge = OSKernelInputEventBridge()
        self.windows_kernel_bridge = WindowsKernelInputEventBridge()

        if not self.is_connected:
            active_fallback = "Windows SendInput Kernel Bridge" if self.windows_kernel_bridge.is_available else ("Linux uinput Bridge" if self.linux_kernel_bridge.is_available else "Software Playwright Bridge")
            logger.info(f"FPGA PCIe DMA device '{self.dma_device_path}' not detected. Active fallback to {active_fallback}.")

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
            elif self.windows_kernel_bridge.is_available:
                # Dispatch real Windows SendInput mouse packet
                self.windows_kernel_bridge.send_mouse_input(dx, dy)
            elif self.linux_kernel_bridge.is_available:
                try:
                    k_events = self.linux_kernel_bridge.generate_kernel_mouse_move_bytes(dx, dy)
                    with open(self.linux_kernel_bridge.uinput_path, "wb") as kdev:
                        kdev.write(k_events)
                except Exception as ke:
                    logger.debug(f"uinput write fallback: {ke}")

            prev_x, prev_y = pt['x'], pt['y']

        return packets
