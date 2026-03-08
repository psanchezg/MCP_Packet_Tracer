"""Use case: corregir plan automáticamente."""

from __future__ import annotations
from ...domain.models.plans import TopologyPlan
from ...domain.services.auto_fixer import fix_plan
from ..dto.responses import FixResponse


def fix_plan_uc(plan: TopologyPlan) -> FixResponse:
    """Intenta corregir un plan automáticamente."""
    fixed_plan, fixes = fix_plan(plan)
    return FixResponse(
        plan_json=fixed_plan.model_dump_json(indent=2),
        fixes_applied=fixes,
        is_valid=fixed_plan.is_valid,
        remaining_errors=[e.to_dict() for e in fixed_plan.errors] if fixed_plan.errors else [],
    )
