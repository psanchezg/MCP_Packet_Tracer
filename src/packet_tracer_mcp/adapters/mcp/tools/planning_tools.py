"""Planning tools — pt_estimate_plan, pt_plan_topology."""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from ....domain.models.requests import TopologyRequest
from ....domain.services.estimator import estimate_from_request
from ....domain.services.orchestrator import plan_from_request
from ....shared.enums import RoutingProtocol, TopologyTemplate
from ....shared.logging import get_logger

logger = get_logger(__name__)


def register_planning_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def pt_estimate_plan(
        routers: int = 2,
        pcs_per_lan: int = 3,
        laptops_per_lan: int = 0,
        switches_per_router: int = 1,
        servers: int = 0,
        access_points: int = 0,
        has_wan: bool = False,
        dhcp: bool = True,
        routing: str = "static",
    ) -> str:
        """
        Quick dry-run estimation without generating a full plan.
        Shows how many devices, links, and subnets will be created.

        Parameters:
        - routers: Number of routers (1-20)
        - pcs_per_lan: PCs per LAN
        - laptops_per_lan: Laptops per LAN (Laptop-PT)
        - switches_per_router: Switches per router
        - servers: Number of servers
        - access_points: Access Points (AccessPoint-PT)
        - has_wan: Include WAN connection
        - dhcp: Configure DHCP
        - routing: static, ospf, eigrp, rip, none
        """
        logger.info("pt_estimate_plan: routers=%d routing=%s", routers, routing)
        request = TopologyRequest(
            routers=routers,
            pcs_per_lan=pcs_per_lan,
            laptops_per_lan=laptops_per_lan,
            switches_per_router=switches_per_router,
            servers=servers,
            access_points=access_points,
            has_wan=has_wan,
            dhcp=dhcp,
            routing=RoutingProtocol(routing),
        )
        est = estimate_from_request(request)
        return json.dumps(est, indent=2, ensure_ascii=False)

    @mcp.tool()
    def pt_plan_topology(
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
        floating_routes: bool = False,
        ospf_process_id: int = 1,
        eigrp_as: int = 100,
    ) -> str:
        """
        Generate a complete network topology plan for Packet Tracer.

        Parameters:
        - routers: Number of routers (1-20)
        - pcs_per_lan: PCs per LAN
        - laptops_per_lan: Laptops per LAN (Laptop-PT)
        - switches_per_router: Switches per router (0-4)
        - servers: Number of servers
        - access_points: Access Points (AccessPoint-PT), one per LAN
        - has_wan: Include WAN connection (Cloud)
        - dhcp: Configure DHCP automatically
        - routing: Routing protocol (static, ospf, eigrp, rip, none)
        - router_model: Router model (1941, 2901, 2911, ISR4321)
        - switch_model: Switch model (2960-24TT, 3560-24PS)
        - template: Template (single_lan, multi_lan, multi_lan_wan, star, hub_spoke,
          branch_office, router_on_a_stick, three_router_triangle, custom)
        - floating_routes: If True with routing=static, adds backup routes with AD=254
        - ospf_process_id: OSPF process ID (1-65535, default 1)
        - eigrp_as: EIGRP AS number (1-65535, default 100)

        Returns the complete plan as JSON.
        """
        logger.info(
            "pt_plan_topology: routers=%d template=%s routing=%s",
            routers, template, routing,
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
        plan, _validation = plan_from_request(request)
        return plan.model_dump_json(indent=2)
