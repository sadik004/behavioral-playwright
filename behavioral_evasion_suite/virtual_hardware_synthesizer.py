"""
Virtual Hardware Synthesizer - Level 5 Quantum Edition
Realtek & Intel Media Device Synthesizer for Headless Containers.
Counters headless detection where navigator.mediaDevices.enumerateDevices() is empty or missing audio/video inputs.
"""

from typing import List, Dict, Any, Optional
import logging
from pydantic import BaseModel, Field

logger = logging.getLogger("BehavioralEvasion.VirtualHardwareSynthesizer")


class MediaDeviceDescriptor(BaseModel):
    """Schema for synthesized media input/output hardware."""
    deviceId: str
    kind: str
    label: str
    groupId: str


class HardwareSynthesisConfig(BaseModel):
    """Configuration for virtual hardware synthesis."""
    audio_inputs: int = Field(default=1, ge=0)
    audio_outputs: int = Field(default=2, ge=0)
    video_inputs: int = Field(default=1, ge=0)
    audio_controller_label: str = Field(default="Realtek High Definition Audio")
    display_camera_label: str = Field(default="Integrated Webcam (04f2:b6b8)")


class VirtualHardwareSynthesizer:
    """
    Synthesizes authentic Realtek & Intel High Definition Audio Controllers and
    integrated cameras for headless Chromium instances and container environments.
    """

    DEFAULT_DEVICES: List[MediaDeviceDescriptor] = [
        MediaDeviceDescriptor(
            deviceId="default",
            kind="audiooutput",
            label="Default - Speakers (Realtek(R) Audio)",
            groupId="62c14041e976db57be0cf11cf69be669d0d3cb1e"
        ),
        MediaDeviceDescriptor(
            deviceId="78adfc238e9a28c117b120f269a9b1c7365021e1a0b38",
            kind="audiooutput",
            label="Speakers (Realtek(R) Audio)",
            groupId="62c14041e976db57be0cf11cf69be669d0d3cb1e"
        ),
        MediaDeviceDescriptor(
            deviceId="default",
            kind="audioinput",
            label="Default - Microphone Array (Intel(R) Smart Sound Technology)",
            groupId="44b82910fa8c823057a60f994918e7782da7010f"
        ),
        MediaDeviceDescriptor(
            deviceId="987bcf12048aa12bb31c9902187f55694200b21a31f28",
            kind="audioinput",
            label="Microphone Array (Intel(R) Smart Sound Technology)",
            groupId="44b82910fa8c823057a60f994918e7782da7010f"
        ),
        MediaDeviceDescriptor(
            deviceId="5821c9fa0120bb37920aa9128fe4017366b901a88b111",
            kind="videoinput",
            label="Integrated Webcam (04f2:b6b8)",
            groupId="9981240182379012379102379102837190283019283"
        )
    ]

    def __init__(self, config: Optional[HardwareSynthesisConfig] = None):
        self.config = config or HardwareSynthesisConfig()

    @classmethod
    def get_synthesized_devices_js(cls) -> str:
        """Generates JS array of media devices to inject into page contexts."""
        devices_json = [d.model_dump() for d in cls.DEFAULT_DEVICES]
        import json
        serialized = json.dumps(devices_json)

        return f"""
        (() => {{
            try {{
                if (window.__virtual_hardware_synthesizer_active__) return;
                window.__virtual_hardware_synthesizer_active__ = true;

                const fakeDevices = {serialized};

                if (!navigator.mediaDevices) {{
                    navigator.mediaDevices = {{}};
                }}

                const origEnumerate = navigator.mediaDevices.enumerateDevices;
                navigator.mediaDevices.enumerateDevices = async function() {{
                    try {{
                        if (origEnumerate) {{
                            const real = await origEnumerate.call(this);
                            if (real && real.length > 0) return real;
                        }}
                    }} catch (e) {{}}
                    return fakeDevices.map(d => Object.assign(Object.create(MediaDeviceInfo.prototype || Object.prototype), d));
                }};

                if (!navigator.mediaDevices.getUserMedia) {{
                    navigator.mediaDevices.getUserMedia = async function(constraints) {{
                        return Promise.reject(new DOMException("Requested device not found", "NotFoundError"));
                    }};
                }}
            }} catch (e) {{}}
        }})();
        """

    def get_script(self) -> str:
        return self.get_synthesized_devices_js()
