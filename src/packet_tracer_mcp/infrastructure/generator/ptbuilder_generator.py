"""
PTBuilder script generator.

Converts a validated TopologyPlan into JavaScript compatible with the
Packet Tracer Builder runtime used by this project.
"""

from __future__ import annotations

import json

from ...domain.models.plans import TopologyPlan
from ...shared.utils import prefix_to_mask


def generate_ptbuilder_script(plan: TopologyPlan) -> str:
    """Generate the base topology script with devices and links only."""
    lines: list[str] = []

    for dev in plan.devices:
        lines.append(
            f'addDevice("{dev.name}", "{dev.model}", {dev.x}, {dev.y});'
        )

    for link in plan.links:
        lines.append(
            f'addLink("{link.device_a}", "{link.port_a}", '
            f'"{link.device_b}", "{link.port_b}", "{link.cable}");'
        )

    return "\n".join(lines)


def generate_executable_script(plan: TopologyPlan) -> str:
    """Generate a full PTBuilder script using runtime-supported calls."""
    from .cli_config_generator import generate_all_configs

    lines: list[str] = [generate_ptbuilder_script(plan)]

    configs = generate_all_configs(plan)
    for device_name, cli_block in configs.items():
        lines.append(
            f'configureIosDevice({json.dumps(device_name)}, '
            f'{json.dumps(cli_block)});'
        )

    pcs = [
        d for d in plan.devices
        if d.category in ("pc", "server", "laptop")
    ]
    for pc in pcs:
        if not pc.interfaces:
            continue
        iface_ip = next(iter(pc.interfaces.values()), None)
        if not iface_ip:
            continue

        ip, prefix = iface_ip.split("/")
        mask = prefix_to_mask(int(prefix))
        gateway = pc.gateway or ""
        use_dhcp = bool(plan.dhcp_pools)

        if use_dhcp:
            lines.append(f'configurePcIp({json.dumps(pc.name)}, true);')
        else:
            lines.append(
                f'configurePcIp({json.dumps(pc.name)}, false, '
                f'{json.dumps(ip)}, {json.dumps(mask)}, '
                f'{json.dumps(gateway)}, "8.8.8.8");'
            )

    return "\n".join(lines)


def generate_full_script(plan: TopologyPlan) -> str:
    """Generate the topology script plus per-device CLI as comments."""
    from .cli_config_generator import generate_all_configs

    parts: list[str] = [generate_ptbuilder_script(plan)]

    configs = generate_all_configs(plan)
    if configs:
        parts.append("/* === CLI configs per device (reference) ===")
        parts.append("   Paste into each device CLI manually. */")
        for device_name, cli_block in configs.items():
            parts.append(f"/* --- {device_name} ---")
            for line in cli_block.splitlines():
                parts.append(line)
            parts.append("*/ ")

    return "\n".join(parts)
