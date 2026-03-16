"""Template engine — renders Jinja2 IOS config templates."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from ...shared.logging import get_logger

logger = get_logger(__name__)

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "shared" / "templates"

_AVAILABLE_TEMPLATES: dict[str, str] = {
    "ospf_basic": "OSPF single/multi-area configuration",
    "eigrp_named": "EIGRP named mode (modern syntax)",
    "vlan_trunk": "VLANs + trunk + access ports",
    "hsrp_pair": "HSRP active/standby pair",
    "nat_overload": "PAT/NAT overload for internet access",
    "acl_dmz": "Extended ACL for DMZ ruleset",
    "dhcp_server": "DHCP pools with exclusions",
    "stp_rapid": "Rapid PVST+ with root priority",
}


def list_available_templates() -> dict[str, str]:
    """Return {template_name: description} for all templates."""
    return dict(_AVAILABLE_TEMPLATES)


def render_template(template_name: str, context: dict) -> list[str]:
    """Render a Jinja2 template and return IOS CLI lines.

    Args:
        template_name: Template name without .j2 extension.
        context: Dict of template variables.

    Returns:
        List of IOS CLI command strings.

    Raises:
        ValueError: If template_name is not found.
    """
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=False,
    )
    try:
        tmpl = env.get_template(f"{template_name}.j2")
    except TemplateNotFound:
        available = ", ".join(_AVAILABLE_TEMPLATES.keys())
        raise ValueError(
            f"Template '{template_name}' not found. Available: {available}"
        ) from None

    rendered = tmpl.render(**context)
    lines = [line for line in rendered.splitlines() if line.strip()]
    logger.debug("Rendered template '%s': %d lines", template_name, len(lines))
    return lines
