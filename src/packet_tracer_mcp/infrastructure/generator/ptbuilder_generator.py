"""
Generador de scripts PTBuilder.

Convierte un TopologyPlan validado en JavaScript compatible
con la extensión PTBuilder de Packet Tracer.
"""

from __future__ import annotations
from ...domain.models.plans import TopologyPlan


def generate_ptbuilder_script(plan: TopologyPlan) -> str:
    """Genera un script JS de PTBuilder a partir de un plan validado."""
    lines: list[str] = []
    lines.append("// ===========================================")
    lines.append("// Script generado por Packet Tracer MCP")
    lines.append("// ===========================================")
    lines.append("")

    # --- Dispositivos ---
    lines.append("// --- Dispositivos ---")
    for dev in plan.devices:
        lines.append(f'addDevice("{dev.name}", "{dev.model}", {dev.x}, {dev.y});')
    lines.append("")

    # --- Enlaces ---
    lines.append("// --- Enlaces ---")
    for link in plan.links:
        lines.append(
            f'addLink("{link.device_a}", "{link.port_a}", '
            f'"{link.device_b}", "{link.port_b}", "{link.cable}");'
        )
    lines.append("")

    return "\n".join(lines)


def generate_full_script(plan: TopologyPlan) -> str:
    """
    Genera el script completo: PTBuilder + bloque de configuración CLI
    como comentarios.
    """
    from .cli_config_generator import generate_all_configs

    parts: list[str] = []
    parts.append(generate_ptbuilder_script(plan))

    configs = generate_all_configs(plan)
    if configs:
        parts.append("// ===========================================")
        parts.append("// Configuraciones CLI por dispositivo")
        parts.append("// ===========================================")
        parts.append("//")
        parts.append("// Copiar y pegar en la CLI de cada dispositivo,")
        parts.append("// o usar una extensión que soporte envío de CLI.")
        parts.append("//")
        for device_name, cli_block in configs.items():
            parts.append(f"// --- {device_name} ---")
            for line in cli_block.splitlines():
                parts.append(f"// {line}")
            parts.append("//")

    return "\n".join(parts)
