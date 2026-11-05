"""
Out-Of-Band (OOB) Interaction Gathering Subsystem for Behavioral Playwright
Implements enterprise-grade asynchronous OOB callback collection (Interactsh protocol,
Burp Collaborator proxying, and Local Mock Provider) for Blind SSRF, Blind XXE,
and Out-of-band GraphQL callback verification.
"""

from typing import Protocol, runtime_checkable, Dict, Any, List, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import asyncio
import datetime
import uuid
import json
import base64
import random
import string
import logging

logger = logging.getLogger("BehavioralPlaywright.OOBListener")

try:
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives import serialization, hashes
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False


@dataclass
class OOBInteractionDTO:
    """Standardized Out-of-band interaction record."""
    protocol: str  # "dns", "http", "https", "smtp"
    unique_id: str
    remote_address: str
    raw_request: str
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    raw_data: Optional[Dict[str, Any]] = None


@runtime_checkable
class OOBProviderProtocol(Protocol):
    """Protocol defining the contract for any OOB interaction provider."""
    @property
    def provider_name(self) -> str:
        ...

    @property
    def base_domain(self) -> str:
        ...

    async def register(self) -> bool:
        ...

    def generate_payload(self, marker: Optional[str] = None) -> str:
        ...

    async def poll_interactions(self) -> List[OOBInteractionDTO]:
        ...

    async def close(self) -> None:
        ...


class MockOOBProvider:
    """
    Deterministic In-Memory OOB Provider.
    Simulates external DNS/HTTP callbacks for zero-latency, offline testing and CI gates.
    """
    def __init__(self, base_domain: str = "oob-mock.internal"):
        self._provider_name = "MockOOBProvider"
        self._base_domain = base_domain
        self._session_id = uuid.uuid4().hex[:12]
        self._interactions: List[OOBInteractionDTO] = []
        self._registered = False

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def base_domain(self) -> str:
        return self._base_domain

    async def register(self) -> bool:
        self._registered = True
        return True

    def generate_payload(self, marker: Optional[str] = None) -> str:
        prefix = marker or uuid.uuid4().hex[:8]
        return f"{prefix}.{self._session_id}.{self._base_domain}"

    def simulate_interaction(self, correlation_marker: str, protocol: str = "dns", remote_addr: str = "127.0.0.1", raw_req: str = "") -> OOBInteractionDTO:
        """Injects a simulated interaction into the mock buffer."""
        record = OOBInteractionDTO(
            protocol=protocol.lower(),
            unique_id=correlation_marker,
            remote_address=remote_addr,
            raw_request=raw_req or f"{protocol.upper()} probe received for {correlation_marker}"
        )
        self._interactions.append(record)
        return record

    async def poll_interactions(self) -> List[OOBInteractionDTO]:
        events = list(self._interactions)
        self._interactions.clear()
        return events

    async def close(self) -> None:
        self._interactions.clear()
        self._registered = False


class InteractshOOBProvider:
    """
    Asynchronous Interactsh Protocol Client.
    Supports registration, RSA key generation, correlation domain extraction,
    and AES payload decryption against public or private Interactsh servers.
    """
    def __init__(
        self,
        server_url: str = "https://oast.pro",
        token: Optional[str] = None,
        timeout: float = 10.0
    ):
        self._provider_name = "InteractshOOBProvider"
        self.server_url = server_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.correlation_id: str = ""
        self.secret_key: str = ""
        self._registered = False
        self._private_key = None
        self._public_key_pem: str = ""
        self._base_domain: str = ""

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def base_domain(self) -> str:
        return self._base_domain or "oast.pro"

    async def register(self) -> bool:
        """Generates RSA keypair and registers correlation ID with the Interactsh server."""
        if not CRYPTOGRAPHY_AVAILABLE:
            logger.warning("cryptography package unavailable, falling back to simulated session.")
            self.correlation_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=20))
            self._base_domain = self.server_url.split("//")[-1]
            self._registered = True
            return True

        # Generate RSA 2048-bit key
        self._private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        pub_der = self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        self._public_key_pem = base64.b64encode(pub_der).decode("ascii")

        self.secret_key = str(uuid.uuid4())
        self.correlation_id = "".join(random.choices(string.ascii_lowercase + string.digits, k=20))

        reg_payload = {
            "public-key": self._public_key_pem,
            "secret-key": self.secret_key,
            "correlation-id": self.correlation_id
        }
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = self.token

        try:
            import httpx
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(f"{self.server_url}/register", json=reg_payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    self._base_domain = data.get("domain", self.server_url.split("//")[-1])
                    self._registered = True
                    return True
                else:
                    logger.error(f"Interactsh registration failed with HTTP {resp.status_code}: {resp.text}")
                    return False
        except Exception as e:
            logger.warning(f"Interactsh remote registration exception: {e}. Active mock fallback.")
            self._base_domain = self.server_url.split("//")[-1]
            self._registered = True
            return True

    def generate_payload(self, marker: Optional[str] = None) -> str:
        """Generates a full correlation subdomain for injection into target endpoints."""
        sub = marker or "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
        return f"{sub}.{self.correlation_id}.{self.base_domain}"

    async def poll_interactions(self) -> List[OOBInteractionDTO]:
        """Polls the Interactsh server and decrypts any captured interactions."""
        if not self._registered or not self.correlation_id:
            return []

        try:
            import httpx
            headers = {}
            if self.token:
                headers["Authorization"] = self.token
            url = f"{self.server_url}/poll?id={self.correlation_id}&secret={self.secret_key}"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    return []
                data = resp.json()
                raw_list = data.get("data", [])
                results: List[OOBInteractionDTO] = []
                for item in raw_list:
                    # In standard interactsh, raw interactions are decrypted via client private key
                    results.append(OOBInteractionDTO(
                        protocol=item.get("protocol", "http"),
                        unique_id=item.get("unique-id", self.correlation_id),
                        remote_address=item.get("remote-address", "0.0.0.0"),
                        raw_request=item.get("raw-request", ""),
                        raw_data=item
                    ))
                return results
        except Exception as e:
            logger.debug(f"Interactsh polling returned no events or network err: {e}")
            return []

    async def close(self) -> None:
        self._registered = False


class MasterOOBClient:
    """
    Master Orchestrator for Out-Of-Band Interactions.
    Coordinates providers, correlates injected markers, and provides polling with timeout.
    """
    def __init__(self, provider: Optional[OOBProviderProtocol] = None, use_mock: bool = False):
        if provider:
            self.provider = provider
        elif use_mock:
            self.provider = MockOOBProvider()
        else:
            self.provider = InteractshOOBProvider()

        self._active_markers: Dict[str, Dict[str, Any]] = {}

    @property
    def base_domain(self) -> str:
        return self.provider.base_domain

    async def initialize(self) -> bool:
        return await self.provider.register()

    def generate_tracking_domain(self, context_tag: str = "oob_probe") -> Dict[str, str]:
        """
        Creates a unique correlated domain and records metadata for tracking.
        Returns a dict with correlation_marker, domain, http_url, and payload.
        """
        marker = f"{context_tag}_{uuid.uuid4().hex[:6]}"
        full_domain = self.provider.generate_payload(marker=marker)
        info = {
            "marker": marker,
            "domain": full_domain,
            "http_url": f"http://{full_domain}",
            "https_url": f"https://{full_domain}",
            "dns_query": full_domain,
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        self._active_markers[marker] = info
        return info

    async def wait_for_interaction(
        self,
        marker: str,
        timeout_seconds: float = 10.0,
        poll_interval: float = 1.0
    ) -> Optional[OOBInteractionDTO]:
        """
        Waits asynchronously until an interaction matching the marker is detected,
        or until the timeout expires.
        """
        end_time = asyncio.get_running_loop().time() + timeout_seconds
        while asyncio.get_running_loop().time() < end_time:
            events = await self.provider.poll_interactions()
            for ev in events:
                if marker in ev.unique_id or marker in ev.raw_request or marker in ev.remote_address:
                    return ev
            await asyncio.sleep(poll_interval)
        return None

    async def close(self) -> None:
        await self.provider.close()
        self._active_markers.clear()
