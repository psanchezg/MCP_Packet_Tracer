"""Topology intelligence engine — analyze descriptions, suggest improvements, calculate addressing."""

from __future__ import annotations

import ipaddress
import re

from ..models.plans import TopologyPlan
from ..models.topology_analysis import (
    AddressEntry,
    AddressingPlan,
    ConfigValidationError,
    Improvement,
    SiteInfo,
    TopologyAnalysis,
)

# ---------------------------------------------------------------------------
# Keyword maps for NLP-lite parsing
# ---------------------------------------------------------------------------

_SITE_PATTERNS: list[tuple[str, str]] = [
    (r"(?:sede\s*(?:central|principal)|HQ|headquarter|oficina\s*central|matriz)", "HQ"),
    (r"(?:sucursal|branch|oficina\s*remota|remote)", "branch"),
    (r"(?:datacenter|data\s*center|DC|centro\s*de\s*datos)", "DC"),
    (r"(?:DMZ|zona\s*desmilitarizada|demilitarized)", "DMZ"),
]

_ROUTING_KEYWORDS: dict[str, str] = {
    "ospf": "OSPF",
    "eigrp": "EIGRP",
    "rip": "RIP",
    "static": "static",
    "estatic": "static",
    "dinamico": "OSPF",
    "dynamic": "OSPF",
}

_FEATURE_PATTERNS: dict[str, str] = {
    r"(?:redundan|alta\s*disponibilidad|HA|high.avail|dual|backup)": "redundancy",
    r"(?:DMZ|zona\s*desmilitarizada|demilitarized)": "dmz",
    r"(?:WAN|inter.?site|sitio.?a.?sitio|site.to.site|serial)": "wan",
    r"(?:NAT|PAT|internet|acceso\s*a\s*internet|salida)": "nat",
    r"(?:servidor|server|web|correo|mail|dns|http)": "server",
    r"(?:VLAN|segmentac|segmentar)": "vlan",
}


def _count_pattern(text: str, pattern: str) -> int:
    """Count occurrences of a number near a pattern."""
    # Wrap alternations so the digit group binds correctly
    wrapped = f"(?:{pattern})"
    m = re.search(rf"(\d+)\s*{wrapped}", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(rf"{wrapped}\s*(?:con|with|de|:)?\s*(\d+)", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return 0


# ---------------------------------------------------------------------------
# analyze_topology
# ---------------------------------------------------------------------------


def analyze_topology(description: str) -> TopologyAnalysis:
    """Parse a natural language description into a structured topology analysis."""
    text = description.lower()
    sites: list[SiteInfo] = []
    features: set[str] = set()

    # Detect features
    for pat, feat in _FEATURE_PATTERNS.items():
        if re.search(pat, text, re.IGNORECASE):
            features.add(feat)

    # Detect routing
    routing = "OSPF"  # default for multi-site
    for kw, proto in _ROUTING_KEYWORDS.items():
        if kw in text:
            routing = proto
            break

    # Detect sites
    for pat, site_type in _SITE_PATTERNS:
        matches = re.findall(pat, text, re.IGNORECASE)
        if matches:
            count = _count_pattern(text, pat) or len(matches)
            for i in range(max(1, count)):
                name = f"{site_type}" if count <= 1 else f"{site_type}-{i + 1}"
                sites.append(SiteInfo(
                    name=name,
                    type=site_type,
                    routers=2 if site_type == "HQ" else 1,
                    switches=2 if site_type in ("HQ", "DC") else 1,
                    pcs=10 if site_type == "HQ" else 5 if site_type == "branch" else 2,
                    servers=3 if site_type == "DC" else (1 if site_type == "DMZ" else 0),
                ))

    # Count explicit branches
    branch_count = _count_pattern(text, r"sucursal|branch")
    if branch_count > 0 and not any(s.type == "branch" for s in sites):
        for i in range(branch_count):
            sites.append(SiteInfo(
                name=f"Branch-{i + 1}", type="branch",
                routers=1, switches=1, pcs=5,
            ))

    # Default: if no sites detected, create a simple one
    if not sites:
        router_count = _count_pattern(text, r"router") or 2
        pc_count = _count_pattern(text, r"(?:pc|computador|host|estacion)") or 3
        sites.append(SiteInfo(
            name="Main", type="HQ",
            routers=router_count, switches=max(1, router_count),
            pcs=pc_count,
        ))
        if len(sites) == 1 and sites[0].routers == 1:
            routing = "static"

    # If no HQ but has branches, add an HQ
    if any(s.type == "branch" for s in sites) and not any(s.type == "HQ" for s in sites):
        sites.insert(0, SiteInfo(
            name="HQ", type="HQ", routers=2, switches=2, pcs=10,
        ))

    # Calculate totals
    total_devices = sum(s.routers + s.switches + s.pcs + s.servers for s in sites)
    for site in sites:
        site.device_count = site.routers + site.switches + site.pcs + site.servers

    # Generate subnet suggestions
    subnets: list[dict[str, str]] = []
    lan_gen = ipaddress.IPv4Network("192.168.0.0/16").subnets(new_prefix=24)
    link_gen = ipaddress.IPv4Network("10.0.0.0/16").subnets(new_prefix=30)
    for site in sites:
        net = next(lan_gen)
        subnets.append({
            "site": site.name, "type": "LAN",
            "network": str(net), "description": f"{site.name} LAN",
        })
    # Inter-site links
    if len(sites) > 1:
        for i in range(len(sites) - 1):
            net = next(link_gen)
            subnets.append({
                "site": f"{sites[i].name}-{sites[i + 1].name}",
                "type": "WAN", "network": str(net),
                "description": f"Link {sites[i].name} <-> {sites[i + 1].name}",
            })

    # Suggest models based on size
    if total_devices > 30:
        models = {"router": "ISR4321", "switch": "3560-24PS"}
    elif total_devices > 15:
        models = {"router": "2911", "switch": "2960-24TT"}
    else:
        models = {"router": "2901", "switch": "2960-24TT"}

    return TopologyAnalysis(
        description=description,
        sites=sites,
        routing_protocol=routing,
        has_redundancy="redundancy" in features,
        has_dmz="dmz" in features,
        has_wan="wan" in features or len(sites) > 1,
        has_nat="nat" in features,
        total_devices=total_devices,
        subnets=subnets,
        suggested_models=models,
    )


# ---------------------------------------------------------------------------
# suggest_improvements
# ---------------------------------------------------------------------------


def suggest_improvements(plan: TopologyPlan) -> list[Improvement]:
    """Analyze an existing topology and suggest improvements."""
    improvements: list[Improvement] = []
    routers = plan.devices_by_category("router")
    switches = plan.devices_by_category("switch")

    # Build connectivity map
    connected: dict[str, set[str]] = {d.name: set() for d in plan.devices}
    for link in plan.links:
        connected[link.device_a].add(link.device_b)
        connected[link.device_b].add(link.device_a)

    # Orphaned devices (no connections)
    for dev in plan.devices:
        if not connected.get(dev.name):
            improvements.append(Improvement(
                category="connectivity",
                severity="error",
                device=dev.name,
                message=f"Device '{dev.name}' has no connections (orphaned node).",
                fix=f"Connect {dev.name} to the network via a switch or router.",
            ))

    # Router with only 1 interface configured
    for r in routers:
        if len(r.interfaces) <= 1:
            improvements.append(Improvement(
                category="scalability",
                severity="warn",
                device=r.name,
                message=f"Router '{r.name}' has only {len(r.interfaces)} interface(s) configured.",
                fix="A router needs at least 2 interfaces to route between networks.",
            ))

    # No redundancy — single switch per site
    if len(switches) > 0 and len(routers) > 0:
        router_to_switches: dict[str, int] = {r.name: 0 for r in routers}
        for link in plan.links:
            if link.device_a in router_to_switches and any(
                s.name == link.device_b for s in switches
            ):
                router_to_switches[link.device_a] += 1
            if link.device_b in router_to_switches and any(
                s.name == link.device_a for s in switches
            ):
                router_to_switches[link.device_b] += 1
        for rname, count in router_to_switches.items():
            if count == 1:
                improvements.append(Improvement(
                    category="redundancy",
                    severity="info",
                    device=rname,
                    message=f"Router '{rname}' connects to only 1 switch (no redundancy).",
                    fix="Add a second switch with redundant uplinks for HA.",
                ))

    # No DHCP configured
    if not plan.dhcp_pools and plan.devices_by_category("pc"):
        improvements.append(Improvement(
            category="best_practice",
            severity="warn",
            message="No DHCP pools configured. PCs need manual IP configuration.",
            fix="Enable DHCP on routers to auto-assign IPs to hosts.",
        ))

    # No routing configured
    has_routing = bool(
        plan.static_routes or plan.ospf_configs
        or plan.rip_configs or plan.eigrp_configs
    )
    if len(routers) > 1 and not has_routing:
        improvements.append(Improvement(
            category="connectivity",
            severity="error",
            message="Multiple routers but no routing protocol configured.",
            fix="Configure OSPF, EIGRP, RIP, or static routes between routers.",
        ))

    # Security: flat network (all PCs on same subnet)
    pc_subnets: set[str] = set()
    for dev in plan.devices:
        if dev.category in ("pc", "laptop"):
            for ip_cidr in dev.interfaces.values():
                net = ipaddress.IPv4Interface(ip_cidr).network
                pc_subnets.add(str(net))
    if len(pc_subnets) == 1 and len(plan.devices_by_category("pc")) > 5:
        improvements.append(Improvement(
            category="security",
            severity="warn",
            message="All PCs are on the same subnet (flat network).",
            fix="Segment the network with VLANs for better security and performance.",
        ))

    # No server isolation
    servers = plan.devices_by_category("server")
    if servers:
        server_subnets = set()
        pc_nets = set()
        for s in servers:
            for ip_cidr in s.interfaces.values():
                server_subnets.add(str(ipaddress.IPv4Interface(ip_cidr).network))
        for p in plan.devices_by_category("pc"):
            for ip_cidr in p.interfaces.values():
                pc_nets.add(str(ipaddress.IPv4Interface(ip_cidr).network))
        if server_subnets & pc_nets:
            improvements.append(Improvement(
                category="security",
                severity="warn",
                message="Servers share subnet with PCs (no DMZ/isolation).",
                fix="Place servers on a dedicated subnet or DMZ for security.",
            ))

    return improvements


# ---------------------------------------------------------------------------
# calculate_addressing
# ---------------------------------------------------------------------------


def calculate_addressing(
    sites: list[dict[str, str | int]],
    vlans: list[dict[str, str | int]] | None = None,
    enable_ipv6: bool = False,
) -> AddressingPlan:
    """Auto-generate a complete IP addressing plan.

    Args:
        sites: List of dicts with keys: name, routers (int), pcs (int), etc.
        vlans: Optional list of VLANs with keys: id, name, site.
        enable_ipv6: If True, include IPv6 dual-stack addresses.

    Returns:
        Complete AddressingPlan with per-device, per-interface entries.
    """
    result = AddressingPlan()
    lan_gen = ipaddress.IPv4Network("192.168.0.0/16").subnets(new_prefix=24)
    link_gen = ipaddress.IPv4Network("10.0.0.0/16").subnets(new_prefix=30)
    loopback_gen = ipaddress.IPv4Network("1.1.1.0/24").hosts()
    ipv6_base = 0x2001_0DB8_0001_0000
    vlan_entries: list[dict[str, str]] = []

    # Process each site
    for site_idx, site in enumerate(sites):
        site_name = str(site.get("name", f"Site-{site_idx + 1}"))
        n_routers = int(site.get("routers", 1))
        n_pcs = int(site.get("pcs", 3))

        for r in range(n_routers):
            rname = f"{site_name}-R{r + 1}" if n_routers > 1 else f"{site_name}-R1"
            device_ifaces: dict[str, AddressEntry] = {}

            # Loopback
            lo_ip = next(loopback_gen)
            device_ifaces["Loopback0"] = AddressEntry(
                ip=str(lo_ip), mask="255.255.255.255", prefix=32,
                description=f"{rname} Router-ID",
                ipv6=f"2001:DB8:{site_idx + 1}::{'%X' % (r + 1)}/128" if enable_ipv6 else "",
                ipv6_prefix=128,
            )

            # LAN interface
            lan_subnet = next(lan_gen)
            lan_hosts = list(lan_subnet.hosts())
            gw_ip = str(lan_hosts[0])
            device_ifaces["GigabitEthernet0/0"] = AddressEntry(
                ip=gw_ip, mask=str(lan_subnet.netmask), prefix=24,
                description=f"{site_name} LAN",
                ipv6=f"2001:DB8:{site_idx + 1}:{r + 1}::1/64" if enable_ipv6 else "",
                ipv6_prefix=64,
            )

            result.devices[rname] = device_ifaces
            result.summary.append(
                f"{rname} GigabitEthernet0/0: {gw_ip}/24 ({site_name} LAN)"
            )

            # PCs
            for p in range(n_pcs):
                pc_name = f"{site_name}-PC{p + 1}"
                host_idx = p + 1
                if host_idx < len(lan_hosts):
                    pc_ip = str(lan_hosts[host_idx])
                    result.devices[pc_name] = {
                        "FastEthernet0": AddressEntry(
                            ip=pc_ip, mask=str(lan_subnet.netmask), prefix=24,
                            description=f"{site_name} host",
                            ipv6=(
                                f"2001:DB8:{site_idx + 1}:{r + 1}::{hex(host_idx + 1)[2:]}/64"
                                if enable_ipv6 else ""
                            ),
                            ipv6_prefix=64,
                        ),
                    }

    # Inter-site WAN links
    router_names = [
        name for name in result.devices if name.endswith("-R1")
    ]
    for i in range(len(router_names) - 1):
        r1_name = router_names[i]
        r2_name = router_names[i + 1]
        wan_subnet = next(link_gen)
        wan_hosts = list(wan_subnet.hosts())

        iface_num = len(result.devices[r1_name])
        iface_a = f"GigabitEthernet0/{iface_num}"
        iface_b = "GigabitEthernet0/1"

        result.devices[r1_name][iface_a] = AddressEntry(
            ip=str(wan_hosts[0]), mask=str(wan_subnet.netmask), prefix=30,
            description=f"WAN to {r2_name}",
            ipv6=f"2001:DB8:FFFF:{i + 1}::1/126" if enable_ipv6 else "",
            ipv6_prefix=126,
        )
        result.devices[r2_name][iface_b] = AddressEntry(
            ip=str(wan_hosts[1]), mask=str(wan_subnet.netmask), prefix=30,
            description=f"WAN to {r1_name}",
            ipv6=f"2001:DB8:FFFF:{i + 1}::2/126" if enable_ipv6 else "",
            ipv6_prefix=126,
        )
        result.summary.append(
            f"WAN {r1_name} <-> {r2_name}: {wan_subnet} (/30)"
        )

    # VLANs
    if vlans:
        for vlan in vlans:
            vlan_id = str(vlan.get("id", "10"))
            vlan_name = str(vlan.get("name", f"VLAN{vlan_id}"))
            vlan_subnet = next(lan_gen)
            vlan_entries.append({
                "id": vlan_id,
                "name": vlan_name,
                "network": str(vlan_subnet),
                "gateway": str(list(vlan_subnet.hosts())[0]),
            })
    result.vlans = vlan_entries

    return result


# ---------------------------------------------------------------------------
# validate_config (per-device config checking)
# ---------------------------------------------------------------------------


def validate_config_lines(
    device_name: str,
    config_lines: list[str],
    plan: TopologyPlan,
) -> list[ConfigValidationError]:
    """Validate IOS config lines against a topology plan."""
    errors: list[ConfigValidationError] = []

    # Collect all IPs in the plan
    all_ips: dict[str, str] = {}  # ip -> device_name
    for dev in plan.devices:
        for iface, ip_cidr in dev.interfaces.items():
            ip = ip_cidr.split("/")[0]
            all_ips[ip] = dev.name

    # Collect all hostnames
    hostnames = [d.name for d in plan.devices]

    configured_ifaces: set[str] = set()
    has_no_shutdown: dict[str, bool] = {}
    current_iface: str = ""
    configured_acls: set[str] = set()
    applied_acls: set[str] = set()

    for line in config_lines:
        stripped = line.strip()

        # Track interfaces
        m = re.match(r"interface\s+(\S+)", stripped, re.IGNORECASE)
        if m:
            current_iface = m.group(1)
            configured_ifaces.add(current_iface)
            has_no_shutdown[current_iface] = False

        # Track no shutdown
        if stripped.lower() == "no shutdown" and current_iface:
            has_no_shutdown[current_iface] = True

        # Check IP address conflicts
        m = re.match(r"ip\s+address\s+(\d+\.\d+\.\d+\.\d+)\s+(\S+)", stripped, re.IGNORECASE)
        if m:
            ip = m.group(1)
            if ip in all_ips and all_ips[ip] != device_name:
                errors.append(ConfigValidationError(
                    severity="error", device=device_name,
                    rule="ip_conflict",
                    message=f"IP {ip} already used by {all_ips[ip]}.",
                    fix=f"Change IP on {device_name} to avoid conflict.",
                ))

        # Track hostname
        m = re.match(r"hostname\s+(\S+)", stripped, re.IGNORECASE)
        if m:
            hostname = m.group(1)
            if hostname in hostnames and hostname != device_name:
                errors.append(ConfigValidationError(
                    severity="error", device=device_name,
                    rule="duplicate_hostname",
                    message=f"Hostname '{hostname}' already exists on another device.",
                    fix=f"Use a unique hostname for {device_name}.",
                ))

        # Track ACLs
        m = re.match(r"(?:ip\s+)?access-list\s+(?:standard|extended)?\s*(\S+)", stripped, re.IGNORECASE)
        if m:
            configured_acls.add(m.group(1))
        m = re.match(r"ip\s+access-group\s+(\S+)", stripped, re.IGNORECASE)
        if m:
            applied_acls.add(m.group(1))

    # Check missing no shutdown
    for iface, has_ns in has_no_shutdown.items():
        if not has_ns:
            errors.append(ConfigValidationError(
                severity="warn", device=device_name,
                rule="missing_no_shutdown",
                message=f"Interface {iface} configured but missing 'no shutdown'.",
                fix=f"Add 'no shutdown' under interface {iface}.",
            ))

    # Check ACL applied but not defined
    for acl in applied_acls - configured_acls:
        errors.append(ConfigValidationError(
            severity="error", device=device_name,
            rule="acl_not_defined",
            message=f"ACL '{acl}' applied but never defined.",
            fix=f"Define access-list {acl} or remove the access-group.",
        ))
    for acl in configured_acls - applied_acls:
        errors.append(ConfigValidationError(
            severity="info", device=device_name,
            rule="acl_not_applied",
            message=f"ACL '{acl}' defined but not applied to any interface.",
            fix=f"Apply '{acl}' with 'ip access-group {acl} in/out' or remove it.",
        ))

    return errors


# ---------------------------------------------------------------------------
# validate_topology (topology-level checks)
# ---------------------------------------------------------------------------


def validate_topology_deep(plan: TopologyPlan) -> list[ConfigValidationError]:
    """Deep topology-level validation beyond basic plan validation."""
    errors: list[ConfigValidationError] = []
    routers = plan.devices_by_category("router")
    switches = plan.devices_by_category("switch")

    # Connectivity map
    connected: dict[str, set[str]] = {d.name: set() for d in plan.devices}
    for link in plan.links:
        connected[link.device_a].add(link.device_b)
        connected[link.device_b].add(link.device_a)

    # Orphaned nodes
    for dev in plan.devices:
        if not connected.get(dev.name):
            errors.append(ConfigValidationError(
                severity="error", device=dev.name,
                rule="orphaned_device",
                message=f"Device '{dev.name}' has no connections.",
                fix=f"Connect {dev.name} to the network.",
            ))

    # Router with only 1 interface
    for r in routers:
        if len(r.interfaces) == 1:
            errors.append(ConfigValidationError(
                severity="warn", device=r.name,
                rule="single_interface_router",
                message=f"Router '{r.name}' has only 1 interface (useless routing).",
                fix="Connect to at least 2 networks for routing to work.",
            ))

    # Loops without STP
    if len(switches) > 1:
        switch_names = {s.name for s in switches}
        switch_edges: list[tuple[str, str]] = []
        for link in plan.links:
            if link.device_a in switch_names and link.device_b in switch_names:
                switch_edges.append((link.device_a, link.device_b))
        if len(switch_edges) >= len(switch_names):
            errors.append(ConfigValidationError(
                severity="warn",
                rule="loop_without_stp",
                message="Switch loop detected. Spanning Tree (STP) should be configured.",
                fix="Enable Rapid PVST+ on all switches to prevent broadcast storms.",
            ))

    # Subnet mask mismatch on connected router interfaces
    for link in plan.links:
        dev_a = plan.device_by_name(link.device_a)
        dev_b = plan.device_by_name(link.device_b)
        if not dev_a or not dev_b:
            continue
        if dev_a.category == "router" and dev_b.category == "router":
            ip_a = dev_a.interfaces.get(link.port_a, "")
            ip_b = dev_b.interfaces.get(link.port_b, "")
            if ip_a and ip_b:
                try:
                    net_a = ipaddress.IPv4Interface(ip_a).network
                    net_b = ipaddress.IPv4Interface(ip_b).network
                    if net_a != net_b:
                        errors.append(ConfigValidationError(
                            severity="error",
                            device=f"{dev_a.name}/{dev_b.name}",
                            rule="subnet_mismatch",
                            message=(
                                f"Subnet mismatch: {dev_a.name}:{link.port_a}={ip_a} "
                                f"vs {dev_b.name}:{link.port_b}={ip_b}"
                            ),
                            fix="Both ends of a link must be on the same subnet.",
                        ))
                except ValueError:
                    pass

    # OSPF network statements covering actual interfaces
    for ospf in plan.ospf_configs:
        router = plan.device_by_name(ospf.router)
        if not router:
            continue
        for net_entry in ospf.networks:
            net_str = net_entry.get("network", "")
            wildcard = net_entry.get("wildcard", "")
            if not net_str or not wildcard:
                continue
            covered = False
            try:
                mask_int = int(ipaddress.IPv4Address(wildcard)) ^ 0xFFFFFFFF
                prefix = bin(mask_int).count("1")
                ospf_net = ipaddress.IPv4Network(f"{net_str}/{prefix}", strict=False)
                for ip_cidr in router.interfaces.values():
                    iface = ipaddress.IPv4Interface(ip_cidr)
                    if iface.ip in ospf_net:
                        covered = True
                        break
            except ValueError:
                covered = True  # can't parse, skip
            if not covered:
                errors.append(ConfigValidationError(
                    severity="warn", device=ospf.router,
                    rule="ospf_no_matching_interface",
                    message=f"OSPF network {net_str} {wildcard} matches no interface on {ospf.router}.",
                    fix="Verify OSPF network statements match configured interface subnets.",
                ))

    return errors
