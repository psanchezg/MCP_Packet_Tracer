"""Models for topology intelligence engine — analysis, improvements, addressing."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SiteInfo(BaseModel):
    """A logical site within a topology."""

    name: str
    type: str = "branch"  # HQ, branch, DC, DMZ
    device_count: int = 0
    routers: int = 1
    switches: int = 1
    pcs: int = 3
    servers: int = 0


class TopologyAnalysis(BaseModel):
    """Result of analyzing a natural language topology description."""

    description: str = ""
    sites: list[SiteInfo] = Field(default_factory=list)
    routing_protocol: str = "OSPF"
    has_redundancy: bool = False
    has_dmz: bool = False
    has_wan: bool = False
    has_nat: bool = False
    total_devices: int = 0
    subnets: list[dict[str, str]] = Field(default_factory=list)
    suggested_models: dict[str, str] = Field(default_factory=dict)


class Improvement(BaseModel):
    """A suggested improvement for an existing topology."""

    category: str  # redundancy, security, scalability, best_practice
    severity: str = "info"  # error, warn, info
    device: str = ""
    message: str = ""
    fix: str = ""


class AddressEntry(BaseModel):
    """A single interface addressing entry."""

    ip: str
    mask: str
    prefix: int = 24
    description: str = ""
    ipv6: str = ""
    ipv6_prefix: int = 64


class AddressingPlan(BaseModel):
    """Complete IP addressing plan for a topology."""

    devices: dict[str, dict[str, AddressEntry]] = Field(default_factory=dict)
    summary: list[str] = Field(default_factory=list)
    vlans: list[dict[str, str]] = Field(default_factory=list)


class ConfigValidationError(BaseModel):
    """A structured config validation error."""

    severity: str = "error"  # error, warn, info
    device: str = ""
    rule: str = ""
    message: str = ""
    fix: str = ""
