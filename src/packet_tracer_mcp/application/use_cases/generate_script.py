"""Use case: generar script PTBuilder."""

from __future__ import annotations

from ...domain.models.plans import TopologyPlan
from ...infrastructure.generator.ptbuilder_generator import (
    generate_full_script,
    generate_ptbuilder_script,
)


def generate_script_uc(plan: TopologyPlan, include_configs: bool = True) -> str:
    """Genera el script PTBuilder."""
    if include_configs:
        return generate_full_script(plan)
    return generate_ptbuilder_script(plan)
