"""Infrastructure catalog."""

from .aliases import MODEL_ALIASES
from .cables import CABLE_RULES, CABLE_TYPES, infer_cable
from .devices import (
    ALL_MODELS,
    DeviceModel,
    PortSpec,
    get_ports_by_speed,
    get_valid_ports,
    resolve_model,
)
from .templates import TEMPLATES, TemplateSpec, get_template, list_templates
