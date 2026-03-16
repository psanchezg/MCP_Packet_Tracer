"""Deploy & project tools — export, deploy, list/load projects, docs."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from ....domain.models.plans import TopologyPlan
from ....infrastructure.execution.deploy_executor import DeployExecutor
from ....infrastructure.execution.manual_executor import ManualExecutor
from ....infrastructure.generator.cli_config_generator import (
    generate_all_configs,
    generate_pc_config,
)
from ....infrastructure.generator.ptbuilder_generator import generate_full_script
from ....infrastructure.persistence.project_repository import ProjectRepository
from ....shared.logging import get_logger
from ....shared.utils import prefix_to_mask

logger = get_logger(__name__)


def register_deploy_tools(mcp: FastMCP) -> None:
    """Register deploy and project MCP tools."""

    @mcp.tool()
    def pt_export(
        plan_json: str,
        project_name: str = "topology",
        output_dir: str = "projects",
    ) -> str:
        """
        Export the plan to files: JS script, CLI configs, and JSON.

        Parameters:
        - plan_json: Plan JSON
        - project_name: Project name
        - output_dir: Output directory
        """
        logger.info("pt_export: project=%s", project_name)
        plan = TopologyPlan.model_validate_json(plan_json)
        executor = ManualExecutor(output_dir=output_dir)
        result = executor.execute(plan, project_name=project_name)

        lines = [f"Files exported to {result['project_dir']}:"]
        for key, path in result["files"].items():
            lines.append(f"  - {key}: {path}")
        return "\n".join(lines)

    @mcp.tool()
    def pt_deploy(
        plan_json: str,
        project_name: str = "topology",
        output_dir: str = "projects",
    ) -> str:
        """
        Deploy a plan to Packet Tracer: copy script to Windows clipboard,
        export config files, and generate step-by-step instructions.

        Parameters:
        - plan_json: Plan JSON (output of pt_plan_topology or pt_full_build)
        - project_name: Project name
        - output_dir: Output directory
        """
        logger.info("pt_deploy: project=%s", project_name)
        plan = TopologyPlan.model_validate_json(plan_json)
        executor = DeployExecutor(output_dir=output_dir)
        result = executor.execute(plan, project_name=project_name)

        parts: list[str] = []

        if result["clipboard"]:
            parts.append("SCRIPT COPIED TO CLIPBOARD")
            parts.append("Paste directly in Packet Tracer > Extensions > Scripting")
        else:
            parts.append("FILES EXPORTED (could not copy to clipboard)")
            parts.append(f"Open {result['project_dir']}/topology.js and copy its contents")

        parts.append("")
        parts.append(f"Project: {result['project_dir']}")
        parts.append(f"Devices: {result['devices_count']}")
        parts.append(f"Links: {result['links_count']}")
        parts.append("")

        for key, path in result["files"].items():
            parts.append(f"  {key}: {path}")

        parts.append("")
        parts.append(result["instructions"])

        return "\n".join(parts)

    @mcp.tool()
    def pt_list_projects(output_dir: str = "projects") -> str:
        """
        List saved projects.

        Parameters:
        - output_dir: base projects directory
        """
        logger.debug("pt_list_projects: dir=%s", output_dir)
        repo = ProjectRepository(base_dir=output_dir)
        projects = repo.list_projects()
        if not projects:
            return "No saved projects found."
        return json.dumps(projects, indent=2, ensure_ascii=False)

    @mcp.tool()
    def pt_load_project(project_name: str, output_dir: str = "projects") -> str:
        """
        Load a saved project.

        Parameters:
        - project_name: project name
        - output_dir: base projects directory
        """
        logger.info("pt_load_project: %s", project_name)
        repo = ProjectRepository(base_dir=output_dir)
        plan = repo.load_plan(project_name)
        return plan.model_dump_json(indent=2)

    @mcp.tool()
    def pt_export_documentation(plan_json: str) -> str:
        """
        Generate complete documentation for a topology plan.

        Returns:
        - Addressing table (markdown)
        - Topology description (human-readable summary)
        - Per-device config snippets
        - Verification commands (show commands to verify deployment)

        Parameters:
        - plan_json: Plan JSON
        """
        logger.info("pt_export_documentation called")
        plan = TopologyPlan.model_validate_json(plan_json)
        configs = generate_all_configs(plan)

        # -- Addressing table --
        addr_lines: list[str] = [
            "| Device | Interface | IP Address | Subnet Mask | Gateway |",
            "|--------|-----------|------------|-------------|---------|",
        ]
        for dev in plan.devices:
            if dev.interfaces:
                for iface, ip_cidr in dev.interfaces.items():
                    ip, prefix = ip_cidr.split("/")
                    mask = prefix_to_mask(int(prefix))
                    gw = dev.gateway or "-"
                    addr_lines.append(f"| {dev.name} | {iface} | {ip} | {mask} | {gw} |")
            elif dev.gateway:
                addr_lines.append(f"| {dev.name} | DHCP | auto | auto | {dev.gateway} |")
        addressing_table = "\n".join(addr_lines)

        # -- Topology description --
        routers = plan.devices_by_category("router")
        switches = plan.devices_by_category("switch")
        pcs = plan.devices_by_category("pc")
        desc_parts: list[str] = [
            f"Topology: {len(plan.devices)} devices total",
            f"  Routers: {len(routers)} ({', '.join(r.name for r in routers)})",
            f"  Switches: {len(switches)} ({', '.join(s.name for s in switches)})",
            f"  PCs/Hosts: {len(pcs)}",
            f"  Links: {len(plan.links)}",
        ]
        if plan.dhcp_pools:
            desc_parts.append(f"  DHCP Pools: {len(plan.dhcp_pools)}")
        if plan.static_routes:
            desc_parts.append(f"  Static Routes: {len(plan.static_routes)}")
        if plan.ospf_configs:
            desc_parts.append(f"  OSPF: {len(plan.ospf_configs)} router(s)")
        if plan.rip_configs:
            desc_parts.append(f"  RIP: {len(plan.rip_configs)} router(s)")
        if plan.eigrp_configs:
            desc_parts.append(f"  EIGRP: {len(plan.eigrp_configs)} router(s)")
        topology_description = "\n".join(desc_parts)

        # -- Config snippets --
        config_snippets: dict[str, str] = dict(configs)
        for pc in plan.devices:
            if pc.category in ("pc", "server", "laptop"):
                config_snippets[pc.name] = generate_pc_config(pc)

        # -- Verification commands --
        verify: list[str] = []
        for r in routers:
            verify.append(f"{r.name}: show ip interface brief")
            verify.append(f"{r.name}: show ip route")
        if plan.ospf_configs:
            for r in routers:
                verify.append(f"{r.name}: show ip ospf neighbor")
        if plan.eigrp_configs:
            for r in routers:
                verify.append(f"{r.name}: show ip eigrp neighbors")
        if plan.dhcp_pools:
            for r in routers:
                verify.append(f"{r.name}: show ip dhcp binding")
        if plan.validations:
            for v in plan.validations:
                verify.append(f"{v.from_device}: ping {v.to_target}")

        # -- PTBuilder script --
        script = generate_full_script(plan)

        result = {
            "addressing_table": addressing_table,
            "topology_description": topology_description,
            "config_snippets": config_snippets,
            "verification_commands": verify,
            "ptbuilder_script": script,
        }
        return json.dumps(result, indent=2, ensure_ascii=False)
