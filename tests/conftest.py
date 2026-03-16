"""Shared test fixtures."""
import pytest
from src.packet_tracer_mcp.domain.models.requests import TopologyRequest
from src.packet_tracer_mcp.domain.models.plans import TopologyPlan, DevicePlan, LinkPlan
from src.packet_tracer_mcp.domain.services.orchestrator import plan_from_request
from src.packet_tracer_mcp.shared.enums import RoutingProtocol, TopologyTemplate


@pytest.fixture
def basic_request():
    """A minimal 2-router topology request."""
    return TopologyRequest(routers=2, pcs_per_lan=2, routing=RoutingProtocol.STATIC)


@pytest.fixture
def basic_plan(basic_request):
    """A validated 2-router plan."""
    plan, _ = plan_from_request(basic_request)
    return plan


@pytest.fixture
def ospf_request():
    return TopologyRequest(routers=2, pcs_per_lan=2, routing=RoutingProtocol.OSPF)


@pytest.fixture
def rip_request():
    return TopologyRequest(routers=2, pcs_per_lan=2, routing=RoutingProtocol.RIP)


@pytest.fixture
def eigrp_request():
    return TopologyRequest(routers=2, pcs_per_lan=2, routing=RoutingProtocol.EIGRP)
