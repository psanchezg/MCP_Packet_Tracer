"""
Orquestador principal.

Traduce un TopologyRequest a un TopologyPlan completo
con dispositivos, enlaces, IPs, DHCP y rutas, todo validado.
"""

from __future__ import annotations

from ..models.requests import TopologyRequest
from ..models.plans import TopologyPlan, DevicePlan, LinkPlan, ValidationCheck
from ..models.errors import ValidationResult
from .ip_planner import IPPlanner
from .validator import validate_plan
from ...infrastructure.catalog.devices import (
    resolve_model, get_ports_by_speed,
)
from ...infrastructure.catalog.cables import infer_cable
from ...shared.enums import PortSpeed, DeviceRole
from ...shared.constants import (
    DEFAULT_ROUTER, DEFAULT_SWITCH,
    LAYOUT_X_START, LAYOUT_Y_ROUTER, LAYOUT_Y_SWITCH, LAYOUT_Y_PC,
    LAYOUT_X_SPACING, LAYOUT_PC_X_SPACING, LAYOUT_CLOUD_X_OFFSET,
)


def plan_from_request(request: TopologyRequest) -> tuple[TopologyPlan, ValidationResult]:
    """
    Pipeline completo. Retorna (plan, validation_result).
    """
    plan = TopologyPlan()

    pcs_list = _normalize_pcs(request)

    _create_devices(plan, request, pcs_list)
    _create_links(plan, request, pcs_list)

    ip_planner = IPPlanner(
        lan_base=request.base_network,
        link_base=request.inter_router_network,
    )
    ip_planner.plan_addressing(plan, routing=request.routing, dhcp=request.dhcp)

    _create_validations(plan)

    result = validate_plan(plan)
    return plan, result


def _normalize_pcs(req: TopologyRequest) -> list[int]:
    if isinstance(req.pcs_per_lan, int):
        return [req.pcs_per_lan] * req.routers
    pcs = list(req.pcs_per_lan)
    while len(pcs) < req.routers:
        pcs.append(pcs[-1] if pcs else 3)
    return pcs


def _create_devices(plan: TopologyPlan, req: TopologyRequest, pcs_list: list[int]):
    router_model = req.router_model or DEFAULT_ROUTER
    switch_model = req.switch_model or DEFAULT_SWITCH

    # Routers
    for i in range(req.routers):
        role = DeviceRole.CORE_ROUTER if req.routers == 1 else (
            DeviceRole.EDGE_ROUTER if (i == 0 or i == req.routers - 1) else DeviceRole.CORE_ROUTER
        )
        plan.devices.append(DevicePlan(
            name=f"R{i + 1}", model=router_model, category="router",
            role=role,
            x=LAYOUT_X_START + i * LAYOUT_X_SPACING, y=LAYOUT_Y_ROUTER,
        ))

    # Switches + PCs
    switch_idx = 0
    pc_idx = 0
    for i in range(req.routers):
        for s in range(req.switches_per_router):
            switch_idx += 1
            plan.devices.append(DevicePlan(
                name=f"SW{switch_idx}", model=switch_model, category="switch",
                role=DeviceRole.ACCESS_SWITCH,
                x=LAYOUT_X_START + i * LAYOUT_X_SPACING + s * 120, y=LAYOUT_Y_SWITCH,
            ))
            n_pcs = pcs_list[i] if s == 0 else 0
            for p in range(n_pcs):
                pc_idx += 1
                plan.devices.append(DevicePlan(
                    name=f"PC{pc_idx}", model="PC", category="pc",
                    role=DeviceRole.END_HOST,
                    x=LAYOUT_X_START + i * LAYOUT_X_SPACING - (n_pcs * LAYOUT_PC_X_SPACING // 2) + p * LAYOUT_PC_X_SPACING,
                    y=LAYOUT_Y_PC,
                ))

    # Servers
    for i in range(req.servers):
        plan.devices.append(DevicePlan(
            name=f"SRV{i + 1}", model="Server", category="server",
            role=DeviceRole.SERVER_HOST,
            x=LAYOUT_X_START + (req.routers + 1) * LAYOUT_X_SPACING,
            y=LAYOUT_Y_PC + i * 80,
        ))

    # Cloud / WAN
    if req.has_wan:
        plan.devices.append(DevicePlan(
            name="WAN", model="Cloud-PT", category="cloud",
            role=DeviceRole.WAN_CLOUD,
            x=LAYOUT_X_START + req.routers * LAYOUT_X_SPACING + LAYOUT_CLOUD_X_OFFSET,
            y=LAYOUT_Y_ROUTER,
        ))


def _create_links(plan: TopologyPlan, req: TopologyRequest, pcs_list: list[int]):
    router_model_obj = resolve_model(req.router_model or DEFAULT_ROUTER)
    switch_model_obj = resolve_model(req.switch_model or DEFAULT_SWITCH)
    if not router_model_obj or not switch_model_obj:
        plan.errors.append("Modelo de router o switch no válido")
        return

    routers = plan.devices_by_category("router")
    switches = plan.devices_by_category("switch")
    pcs = plan.devices_by_category("pc")
    servers = plan.devices_by_category("server")
    cloud = next((d for d in plan.devices if d.category == "cloud"), None)

    used: dict[str, list[str]] = {d.name: [] for d in plan.devices}

    def _next_port(name: str, model: str, speed: str) -> str | None:
        m = resolve_model(model)
        if not m:
            return None
        for p in get_ports_by_speed(m, speed):
            if p.full_name not in used[name]:
                used[name].append(p.full_name)
                return p.full_name
        return None

    def _gig(name: str, model: str) -> str | None:
        return _next_port(name, model, PortSpeed.GIGABIT_ETHERNET)

    def _fast(name: str, model: str) -> str | None:
        return _next_port(name, model, PortSpeed.FAST_ETHERNET)

    # Router ↔ Router (cadena)
    for i in range(len(routers) - 1):
        r1, r2 = routers[i], routers[i + 1]
        p1, p2 = _gig(r1.name, r1.model), _gig(r2.name, r2.model)
        if p1 and p2:
            plan.links.append(LinkPlan(
                device_a=r1.name, port_a=p1,
                device_b=r2.name, port_b=p2,
                cable=infer_cable("router", "router"),
            ))

    # Router ↔ Switch
    spr = req.switches_per_router
    for i, router in enumerate(routers):
        for sw in switches[i * spr:(i + 1) * spr]:
            rp, sp = _gig(router.name, router.model), _gig(sw.name, sw.model)
            if rp and sp:
                plan.links.append(LinkPlan(
                    device_a=router.name, port_a=rp,
                    device_b=sw.name, port_b=sp,
                    cable=infer_cable("router", "switch"),
                ))

    # Switch ↔ PCs
    pc_idx = 0
    for i in range(req.routers):
        primary_sw = switches[i * spr] if i * spr < len(switches) else None
        if not primary_sw:
            continue
        for _ in range(pcs_list[i]):
            if pc_idx >= len(pcs):
                break
            pc = pcs[pc_idx]
            sp, pp = _fast(primary_sw.name, primary_sw.model), _fast(pc.name, pc.model)
            if sp and pp:
                plan.links.append(LinkPlan(
                    device_a=primary_sw.name, port_a=sp,
                    device_b=pc.name, port_b=pp,
                    cable=infer_cable("switch", "pc"),
                ))
            pc_idx += 1

    # Switch ↔ Servers
    if servers and switches:
        sw = switches[0]
        for srv in servers:
            sp, srp = _fast(sw.name, sw.model), _fast(srv.name, srv.model)
            if sp and srp:
                plan.links.append(LinkPlan(
                    device_a=sw.name, port_a=sp,
                    device_b=srv.name, port_b=srp,
                    cable=infer_cable("switch", "server"),
                ))

    # Router ↔ Cloud
    if cloud and routers:
        last = routers[-1]
        rp, cp = _gig(last.name, last.model), _fast(cloud.name, cloud.model)
        if rp and cp:
            plan.links.append(LinkPlan(
                device_a=last.name, port_a=rp,
                device_b=cloud.name, port_b=cp,
                cable=infer_cable("router", "cloud"),
            ))


def _create_validations(plan: TopologyPlan):
    pcs = plan.devices_by_category("pc")
    if len(pcs) >= 2:
        plan.validations.append(ValidationCheck(
            check_type="ping", from_device=pcs[0].name,
            to_target=pcs[-1].name, expected="Reply",
        ))
