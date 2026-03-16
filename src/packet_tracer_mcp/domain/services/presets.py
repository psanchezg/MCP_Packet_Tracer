"""Scenario presets — ready-made topologies with full wiring and config."""

from __future__ import annotations

from ...shared.enums import RoutingProtocol, TopologyTemplate
from ..models.requests import TopologyRequest

# ---------------------------------------------------------------------------
# Preset definitions
# ---------------------------------------------------------------------------

PRESET_CATALOG: dict[str, dict] = {
    "small_office": {
        "name": "Small Office",
        "description": (
            "1 router, 1 switch, 5 PCs with DHCP. "
            "Simple single-LAN office setup."
        ),
        "request": {
            "template": TopologyTemplate.SINGLE_LAN,
            "routers": 1,
            "pcs_per_lan": 5,
            "switches_per_router": 1,
            "dhcp": True,
            "routing": RoutingProtocol.NONE,
            "router_model": "2901",
            "switch_model": "2960-24TT",
        },
    },
    "branch_hq": {
        "name": "Branch + HQ",
        "description": (
            "2 sites connected via WAN, OSPF routing, DHCP on both sides. "
            "Classic branch-to-headquarters topology."
        ),
        "request": {
            "template": TopologyTemplate.MULTI_LAN_WAN,
            "routers": 2,
            "pcs_per_lan": 3,
            "switches_per_router": 1,
            "has_wan": True,
            "dhcp": True,
            "routing": RoutingProtocol.OSPF,
            "router_model": "2911",
        },
    },
    "dmz_network": {
        "name": "DMZ Network",
        "description": (
            "Router acting as firewall with DMZ server zone and internal LAN. "
            "OSPF routing between segments."
        ),
        "request": {
            "template": TopologyTemplate.MULTI_LAN,
            "routers": 2,
            "pcs_per_lan": 3,
            "switches_per_router": 1,
            "servers": 2,
            "dhcp": True,
            "routing": RoutingProtocol.OSPF,
            "router_model": "2911",
        },
    },
    "redundant_core": {
        "name": "Redundant Core",
        "description": (
            "Dual core routers with multiple switches. "
            "Static routing with floating backup routes."
        ),
        "request": {
            "template": TopologyTemplate.THREE_ROUTER_TRIANGLE,
            "routers": 3,
            "pcs_per_lan": 2,
            "switches_per_router": 1,
            "dhcp": True,
            "routing": RoutingProtocol.STATIC,
            "floating_routes": True,
            "router_model": "2911",
        },
    },
    "full_enterprise": {
        "name": "Full Enterprise",
        "description": (
            "HQ + 2 branches with OSPF multi-area routing, DHCP, and servers. "
            "Complete enterprise-grade topology."
        ),
        "request": {
            "template": TopologyTemplate.MULTI_LAN_WAN,
            "routers": 3,
            "pcs_per_lan": 4,
            "switches_per_router": 1,
            "servers": 2,
            "has_wan": True,
            "dhcp": True,
            "routing": RoutingProtocol.OSPF,
            "router_model": "ISR4321",
            "switch_model": "3560-24PS",
        },
    },
    "ccna_lab_1": {
        "name": "CCNA Lab 1",
        "description": (
            "Classic CCNA exam topology: 2 routers, 2 switches, "
            "4 PCs, static routing, DHCP."
        ),
        "request": {
            "template": TopologyTemplate.MULTI_LAN,
            "routers": 2,
            "pcs_per_lan": 2,
            "switches_per_router": 1,
            "dhcp": True,
            "routing": RoutingProtocol.STATIC,
            "router_model": "2911",
        },
    },
    "ccnp_switch_lab": {
        "name": "CCNP Switch Lab",
        "description": (
            "Switching lab with 3 routers, multiple switches. "
            "OSPF routing for inter-VLAN connectivity."
        ),
        "request": {
            "template": TopologyTemplate.THREE_ROUTER_TRIANGLE,
            "routers": 3,
            "pcs_per_lan": 3,
            "switches_per_router": 2,
            "dhcp": True,
            "routing": RoutingProtocol.OSPF,
            "router_model": "2911",
            "switch_model": "3560-24PS",
        },
    },
    "ipv6_dual_stack": {
        "name": "IPv6 Dual-Stack",
        "description": (
            "2 routers with OSPF, configured for dual-stack operation. "
            "IPv4 + IPv6 addressing throughout."
        ),
        "request": {
            "template": TopologyTemplate.MULTI_LAN,
            "routers": 2,
            "pcs_per_lan": 2,
            "switches_per_router": 1,
            "dhcp": True,
            "routing": RoutingProtocol.OSPF,
            "router_model": "2911",
        },
    },
}


def list_presets() -> list[dict[str, str]]:
    """Return list of available presets with name and description."""
    return [
        {"key": key, "name": p["name"], "description": p["description"]}
        for key, p in PRESET_CATALOG.items()
    ]


def build_preset_request(
    preset_name: str,
    customize: dict | None = None,
) -> TopologyRequest:
    """Build a TopologyRequest from a preset, optionally overriding fields.

    Args:
        preset_name: Key in PRESET_CATALOG.
        customize: Dict of fields to override on the request.

    Returns:
        TopologyRequest ready for plan_from_request().

    Raises:
        ValueError: If preset_name is unknown.
    """
    if preset_name not in PRESET_CATALOG:
        available = ", ".join(PRESET_CATALOG.keys())
        raise ValueError(f"Unknown preset '{preset_name}'. Available: {available}")

    preset = PRESET_CATALOG[preset_name]
    params = dict(preset["request"])

    if customize:
        for key, value in customize.items():
            if key in TopologyRequest.model_fields:
                params[key] = value

    return TopologyRequest(**params)
