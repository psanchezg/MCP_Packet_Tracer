"""Validation tools — validate, fix, explain plans and configs."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from ....domain.models.plans import TopologyPlan
from ....domain.services.auto_fixer import fix_plan
from ....domain.services.explainer import explain_plan
from ....domain.services.topology_analyzer import validate_config_lines, validate_topology_deep
from ....domain.services.validator import validate_plan
from ....shared.logging import get_logger

logger = get_logger(__name__)


def register_validation_tools(mcp: FastMCP) -> None:
    """Register validation MCP tools."""

    @mcp.tool()
    def pt_validate_plan(plan_json: str) -> str:
        """
        Validate a topology plan. Returns typed errors and warnings.

        Parameters:
        - plan_json: Plan JSON (output of pt_plan_topology)
        """
        logger.info("pt_validate_plan called")
        plan = TopologyPlan.model_validate_json(plan_json)
        result = validate_plan(plan)

        output = result.to_dict()
        if result.is_valid:
            output["summary"] = "Plan is valid. No errors found."
        else:
            output["summary"] = f"Plan has {len(result.errors)} error(s)."
        return json.dumps(output, indent=2, ensure_ascii=False)

    @mcp.tool()
    def pt_fix_plan(plan_json: str) -> str:
        """
        Auto-fix plan errors. Corrects cables, upgrades routers, reassigns ports.

        Parameters:
        - plan_json: Plan JSON to fix
        """
        logger.info("pt_fix_plan called")
        plan = TopologyPlan.model_validate_json(plan_json)
        fixed_plan, fixes = fix_plan(plan)

        return json.dumps({
            "fixes_applied": fixes,
            "fixes_count": len(fixes),
            "is_valid": fixed_plan.is_valid,
            "plan": json.loads(fixed_plan.model_dump_json()),
        }, indent=2, ensure_ascii=False)

    @mcp.tool()
    def pt_explain_plan(plan_json: str) -> str:
        """
        Explain plan decisions in natural language.
        Useful for understanding model, IP, and routing choices.

        Parameters:
        - plan_json: Plan JSON
        """
        logger.debug("pt_explain_plan called")
        plan = TopologyPlan.model_validate_json(plan_json)
        explanations = explain_plan(plan)
        return "\n".join(f"• {e}" for e in explanations)

    @mcp.tool()
    def pt_validate_config(
        device_name: str,
        config_text: str,
        plan_json: str,
    ) -> str:
        """
        Validate IOS configuration lines against the current topology plan.

        Checks for:
        - IP conflicts with other devices
        - Missing 'no shutdown' on configured interfaces
        - Duplicate hostnames
        - ACLs applied but not defined (or defined but not applied)

        Parameters:
        - device_name: Name of the device being configured (e.g. "R1")
        - config_text: Full IOS configuration text (multiline string)
        - plan_json: Plan JSON for cross-reference
        """
        logger.info("pt_validate_config: device=%s", device_name)
        plan = TopologyPlan.model_validate_json(plan_json)
        config_lines = config_text.splitlines()
        errors = validate_config_lines(device_name, config_lines, plan)

        if not errors:
            return json.dumps({
                "valid": True,
                "count": 0,
                "message": f"Configuration for {device_name} looks good!",
                "errors": [],
            }, indent=2)

        return json.dumps({
            "valid": False,
            "count": len(errors),
            "errors": [e.model_dump() for e in errors],
        }, indent=2, ensure_ascii=False)

    @mcp.tool()
    def pt_validate_topology(plan_json: str) -> str:
        """
        Deep topology-level validation beyond basic plan checks.

        Checks for:
        - Orphaned devices (no connections)
        - Loops without STP configured
        - Routers with only 1 interface (useless routing)
        - Subnet mask mismatches on connected links
        - OSPF network statements not matching interfaces

        Parameters:
        - plan_json: Plan JSON
        """
        logger.info("pt_validate_topology called")
        plan = TopologyPlan.model_validate_json(plan_json)
        errors = validate_topology_deep(plan)

        if not errors:
            return json.dumps({
                "valid": True,
                "count": 0,
                "message": "Topology passes all deep validation checks!",
                "errors": [],
            }, indent=2)

        return json.dumps({
            "valid": False,
            "count": len(errors),
            "errors": [e.model_dump() for e in errors],
        }, indent=2, ensure_ascii=False)
