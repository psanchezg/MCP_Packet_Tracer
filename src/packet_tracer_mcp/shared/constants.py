"""Constantes del sistema."""

# Router/switch por defecto
DEFAULT_ROUTER = "2911"
DEFAULT_SWITCH = "2960-24TT"

# Layout — flat topology (backward-compatible defaults)
LAYOUT_X_START = 100
LAYOUT_Y_ROUTER = 100
LAYOUT_Y_SWITCH = 250
LAYOUT_Y_PC = 400
LAYOUT_X_SPACING = 250
LAYOUT_PC_X_SPACING = 80
LAYOUT_CLOUD_X_OFFSET = 150

# Layout — hierarchical topology layers (Y-axis)
LAYOUT_Y_ISP = 50
LAYOUT_Y_FIREWALL = 200
LAYOUT_Y_CORE_ROUTER = 380
LAYOUT_Y_DISTRIBUTION = 560
LAYOUT_Y_ACCESS_SWITCH = 720
LAYOUT_Y_END_DEVICE = 880
LAYOUT_MIN_X_GAP = 150
LAYOUT_MAX_X = 1400
LAYOUT_MAX_Y = 950

# IP defaults
DEFAULT_LAN_BASE = "192.168.0.0/16"
DEFAULT_LINK_BASE = "10.0.0.0/16"
DEFAULT_LAN_PREFIX = 24
DEFAULT_LINK_PREFIX = 30
DEFAULT_DNS = "8.8.8.8"
DEFAULT_LOOPBACK_BASE = "172.16.0.0/16"
DEFAULT_DMZ_BASE = "10.10.0.0/16"
DEFAULT_WAN_BASE = "200.0.0.0/24"

# Capacidades del sistema (para que el LLM sepa qué soportamos)
CAPABILITIES = {
    "version": "0.5.0",
    "routing": ["static", "static_floating", "ospf", "eigrp", "rip", "none"],
    "features": [
        "dhcp", "wan", "switching", "auto_fix", "explain", "dry_run",
        "floating_routes", "ospf_multi_process", "eigrp_as_config",
        "nat_template", "acl_template", "vlan_template", "stp_template",
        "hsrp_template", "topology_intelligence", "scenario_presets",
        "config_validation", "ipv6_addressing", "plan_persistence",
    ],
    "templates": [
        "ospf_basic", "eigrp_named", "vlan_trunk", "hsrp_pair",
        "nat_overload", "acl_dmz", "dhcp_server", "stp_rapid",
    ],
    "device_models": 19,
    "max_routers": 20,
    "max_pcs_per_lan": 24,
    "max_switches_per_router": 4,
}

# Masks lookup
PREFIX_TO_MASK = {
    8:  "255.0.0.0",
    16: "255.255.0.0",
    24: "255.255.255.0",
    25: "255.255.255.128",
    26: "255.255.255.192",
    27: "255.255.255.224",
    28: "255.255.255.240",
    29: "255.255.255.248",
    30: "255.255.255.252",
    32: "255.255.255.255",
}
