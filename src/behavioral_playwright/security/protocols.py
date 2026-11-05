"""
Security Architecture Protocol and Base Abstractions for Behavioral Evasion Suite
Establishes enterprise-grade Clean Architecture contracts for all security auditors.
"""

from typing import Protocol, runtime_checkable, Dict, Any, List, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import datetime


@dataclass
class SecurityFinding:
    title: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL
    cwe_id: str
    description: str
    remediation: str
    evidence: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


@dataclass
class AuditResultDTO:
    auditor_name: str
    status: str
    target: str
    timestamp: str
    findings: List[SecurityFinding] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class SecurityAuditorProtocol(Protocol):
    """
    Enterprise protocol contract enforcing standardized audit interface across all auditors.
    """
    @property
    def auditor_name(self) -> str:
        ...

    async def run_audit(self, target: Any, **kwargs: Any) -> Dict[str, Any]:
        ...


class BaseSecurityAuditor(ABC):
    """
    Abstract Base Class providing standardized reporting and diagnostic tracking.
    """
    def __init__(self, name: str):
        self._name = name

    @property
    def auditor_name(self) -> str:
        return self._name

    @abstractmethod
    async def run_audit(self, target: Any, **kwargs: Any) -> Dict[str, Any]:
        pass
