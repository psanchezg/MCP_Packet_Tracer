"""Generation tools — pt_generate_script, pt_generate_configs, pt_full_build."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ....domain.models.plans import TopologyPlan
from ....domain.models.requests import TopologyRequest
from ....domain.services.estimator import estimate_from_plan
from ....domain.services.explainer import explain_plan
from ....domain.services.orchestrator import plan_from_request
from ....infrastructure.execution.deploy_executor import DeployExecutor
from ....infrastructure.generator.cli_config_generator import (
    generate_all_configs,
    generate_pc_config,
)
from ....infrastructure.generator.ptbuilder_generator import (
    generate_full_script,
    generate_ptbuilder_script,
)
from ....shared.enums import RoutingProtocol, TopologyTemplate
from ....shared.logging import get_logger

logger = get_logger(__name__)


def register_generation_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def pt_generate_script(plan_json: str, include_configs: bool = True) -> str:
        """
        Generate the PTBuilder JavaScript script.

        Parameters:
        - plan_json: Plan JSON
        - include_configs: if True, includes CLI configs as comments
        """
        logger.info("pt_generate_script: include_configs=%s", include_configs)
        plan = TopologyPlan.model_validate_json(plan_json)
        if include_configs:
            return generate_full_script(plan)
        return generate_ptbuilder_script(plan)

    @mcp.tool()
    def pt_generate_configs(plan_json: str) -> str:
        """
        Generate CLI (IOS) configurations for all routers and switches.

        Parameters:
        - plan_json: Plan JSON
        """
        logger.info("pt_generate_configs called")
        plan = TopologyPlan.model_validate_json(plan_json)
        configs = generate_all_configs(plan)

        result_parts: list[str] = []
        for device_name, cli_block in configs.items():
            result_parts.append(f"=== {device_name} ===")
            result_parts.append(cli_block)
            result_parts.append("")

        pcs = [d for d in plan.devices if d.category in ("pc", "server", "laptop")]
        if pcs:
            result_parts.append("=== Host Configuration ===")
            for pc in pcs:
                result_parts.append(generate_pc_config(pc))
                result_parts.append("")

        return "\n".join(result_parts)

    @mcp.tool()
    def pt_full_build(
        routers: int = 2,
        pcs_per_lan: int = 3,
        laptops_per_lan: int = 0,
        switches_per_router: int = 1,
        servers: int = 0,
        access_points: int = 0,
        has_wan: bool = False,
        dhcp: bool = True,
        routing: str = "static",
        router_model: str = "2911",
        switch_model: str = "2960-24TT",
        template: str = "multi_lan",
        deploy: bool = True,
        floating_routes: bool = False,
        ospf_process_id: int = 1,
        eigrp_as: int = 100,
    ) -> str:
        """
        Complete pipeline: plan, validate, generate, explain, estimate, and deploy.

        If deploy=True (default), copies the script to the Windows clipboard
        and generates step-by-step instructions for Packet Tracer.

        Parameters:
        - routers: Number of routers (1-20)
        - pcs_per_lan: PCs per LAN
        - laptops_per_lan: Laptops per LAN (Laptop-PT)
        - switches_per_router: Switches per router
        - servers: Number of servers
        - access_points: Access Points (AccessPoint-PT), one per LAN
        - has_wan: Include WAN connection
        - dhcp: Configure DHCP
        - routing: static, ospf, eigrp, rip, none
        - router_model: 1941, 2901, 2911, ISR4321
        - switch_model: 2960-24TT, 3560-24PS
        - template: single_lan, multi_lan, multi_lan_wan, star, hub_spoke,
          branch_office, router_on_a_stick, three_router_triangle, custom
        - deploy: If True, copies script to clipboard and exports files
        - floating_routes: If True with routing=static, adds backup routes with AD=254
        - ospf_process_id: OSPF process ID (1-65535, default 1)
        - eigrp_as: EIGRP AS number (1-65535, default 100)
        """
        logger.info(
            "pt_full_build: routers=%d template=%s routing=%s deploy=%s",
            routers, template, routing, deploy,
        )
        request = TopologyRequest(
            template=TopologyTemplate(template),
            routers=routers,
            pcs_per_lan=pcs_per_lan,
            laptops_per_lan=laptops_per_lan,
            switches_per_router=switches_per_router,
            servers=servers,
            access_points=access_points,
            has_wan=has_wan,
            dhcp=dhcp,
            routing=RoutingProtocol(routing),
            router_model=router_model,
            switch_model=switch_model,
            floating_routes=floating_routes,
            ospf_process_id=ospf_process_id,
            eigrp_as=eigrp_as,
        )
        plan, validation = plan_from_request(request)
        explanation = explain_plan(plan)
        estimate_from_plan(plan)

        parts: list[str] = []

        # --- Summary ---
        parts.append("=" * 60)
        parts.append("TOPOLOGY SUMMARY")
        parts.append("=" * 60)
        parts.append(f"Devices: {len(plan.devices)}")
        parts.append(f"Links: {len(plan.links)}")
        parts.append(f"DHCP Pools: {len(plan.dhcp_pools)}")
        parts.append(f"Static routes: {len(plan.static_routes)}")
        parts.append(f"OSPF configs: {len(plan.ospf_configs)}")
        parts.append(f"RIP configs: {len(plan.rip_configs)}")
        parts.append(f"EIGRP configs: {len(plan.eigrp_configs)}")
        parts.append("")

        # --- Validation ---
        if validation.is_valid:
            parts.append("Validation: PASS")
        else:
            parts.append("Validation: FAIL")
            for err in validation.errors:
                parts.append(f"  ERROR [{err.code.value}]: {err.message}")
        if validation.warnings:
            for warn in validation.warnings:
                parts.append(f"  WARNING [{warn.code.value}]: {warn.message}")
        parts.append("")

        # --- Explanation ---
        parts.append("=" * 60)
        parts.append("EXPLANATION")
        parts.append("=" * 60)
        for e in explanation:
            parts.append(f"  {e}")
        parts.append("")

        # --- Addressing table ---
        parts.append("=" * 60)
        parts.append("ADDRESSING TABLE")
        parts.append("=" * 60)
        for dev in plan.devices:
            if dev.interfaces:
                parts.append(f"{dev.name} ({dev.model}):")
                for iface, ip in dev.interfaces.items():
                    parts.append(f"  {iface}: {ip}")
                if dev.gateway:
                    parts.append(f"  Gateway: {dev.gateway}")
            elif dev.gateway:
                parts.append(f"{dev.name}: DHCP (Gateway: {dev.gateway})")
        parts.append("")

        # --- PTBuilder script ---
        parts.append("=" * 60)
        parts.append("PTBUILDER SCRIPT")
        parts.append("=" * 60)
        parts.append(generate_full_script(plan))
        parts.append("")

        # --- CLI configs ---
        configs = generate_all_configs(plan)
        parts.append("=" * 60)
        parts.append("CLI CONFIGURATIONS")
        parts.append("=" * 60)
        for device_name, cli_block in configs.items():
            parts.append(f"\n--- {device_name} ---")
            parts.append(cli_block)

        pcs = [d for d in plan.devices if d.category in ("pc", "server", "laptop")]
        if pcs:
            parts.append("\n--- Hosts ---")
            for pc in pcs:
                parts.append(generate_pc_config(pc))

        # --- Suggested validations ---
        if plan.validations:
            parts.append("")
            parts.append("=" * 60)
            parts.append("SUGGESTED VERIFICATIONS")
            parts.append("=" * 60)
            for v in plan.validations:
                parts.append(
                    f"  {v.check_type}: {v.from_device} -> {v.to_target} (expected: {v.expected})"
                )

        # --- Deploy ---
        if deploy:
            parts.append("")
            parts.append("=" * 60)
            parts.append("DEPLOY TO PACKET TRACER")
            parts.append("=" * 60)
            deploy_exec = DeployExecutor(output_dir="projects")
            deploy_result = deploy_exec.execute(
                plan, project_name=f"build_{routers}r_{pcs_per_lan}pc"
            )
            if deploy_result["clipboard"]:
                parts.append("SCRIPT COPIED TO CLIPBOARD")
                parts.append("")
                parts.append("Instructions:")
                parts.append("  1. Open Packet Tracer")
                parts.append("  2. Go to Extensions > Scripting")
                parts.append("  3. Paste (Ctrl+V) and execute")
                parts.append("")
                parts.append(f"Files exported to: {deploy_result['project_dir']}")
                parts.append("  CLI configs in *_config.txt files")
            else:
                parts.append(f"Files exported to: {deploy_result['project_dir']}")
                parts.append("  Copy topology.js and paste in PT > Extensions > Scripting")
            parts.append("")
            parts.append(deploy_result["instructions"])

        # --- Plan JSON ---
        parts.append("")
        parts.append("=" * 60)
        parts.append("PLAN JSON (for programmatic use)")
        parts.append("=" * 60)
        parts.append(plan.model_dump_json(indent=2))

        return "\n".join(parts)
