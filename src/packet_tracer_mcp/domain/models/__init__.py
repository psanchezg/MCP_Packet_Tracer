"""Domain models."""

from .errors import ErrorCode, PlanError, ValidationResult
from .plans import (
    DevicePlan,
    DHCPPool,
    LinkPlan,
    OSPFConfig,
    StaticRoute,
    TopologyPlan,
    ValidationCheck,
)
from .requests import TopologyRequest
