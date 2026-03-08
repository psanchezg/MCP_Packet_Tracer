"""Reglas de validación de cables y enlaces."""

from __future__ import annotations
from ..models.plans import TopologyPlan
from ..models.errors import PlanError, ErrorCode
from ...infrastructure.catalog.devices import resolve_model, get_valid_ports
from ...infrastructure.catalog.cables import CABLE_TYPES, infer_cable


def validate_links(plan: TopologyPlan) -> tuple[list[PlanError], list[PlanError]]:
    """Valida enlaces. Retorna (errors, warnings)."""
    errors: list[PlanError] = []
    warnings: list[PlanError] = []
    port_usage: dict[str, str] = {}

    for link in plan.links:
        desc = f"{link.device_a}:{link.port_a} ↔ {link.device_b}:{link.port_b}"

        dev_a = plan.device_by_name(link.device_a)
        dev_b = plan.device_by_name(link.device_b)

        if dev_a is None:
            errors.append(PlanError(
                code=ErrorCode.DEVICE_NOT_FOUND,
                device=link.device_a,
                message=f"Link referencia dispositivo inexistente '{link.device_a}'.",
            ))
            continue
        if dev_b is None:
            errors.append(PlanError(
                code=ErrorCode.DEVICE_NOT_FOUND,
                device=link.device_b,
                message=f"Link referencia dispositivo inexistente '{link.device_b}'.",
            ))
            continue

        # Puertos válidos
        _check_port(errors, dev_a.name, dev_a.model, link.port_a)
        _check_port(errors, dev_b.name, dev_b.model, link.port_b)

        # Puertos duplicados
        for key, label in [
            (f"{link.device_a}:{link.port_a}", desc),
            (f"{link.device_b}:{link.port_b}", desc),
        ]:
            if key in port_usage:
                errors.append(PlanError(
                    code=ErrorCode.PORT_ALREADY_USED,
                    device=key.split(":")[0],
                    message=f"Puerto {key} ya en uso por {port_usage[key]}.",
                    suggestion="Usar otro puerto disponible o agregar un switch.",
                ))
            else:
                port_usage[key] = label

        # Cable válido
        if link.cable not in CABLE_TYPES:
            errors.append(PlanError(
                code=ErrorCode.INVALID_CABLE_TYPE,
                message=f"Tipo de cable '{link.cable}' desconocido en {desc}.",
                suggestion=f"Cables válidos: {list(CABLE_TYPES.keys())}",
            ))

        # Sugerir cable correcto
        expected = infer_cable(dev_a.category, dev_b.category)
        if link.cable != expected:
            warnings.append(PlanError(
                code=ErrorCode.INVALID_CABLE_TYPE,
                message=f"Cable '{link.cable}' en {desc} podría no ser correcto.",
                suggestion=f"Cable sugerido: '{expected}'",
            ))

    return errors, warnings


def _check_port(errors: list[PlanError], dev_name: str, model_name: str, port: str):
    """Verifica que un puerto exista en el modelo."""
    valid = get_valid_ports(model_name)
    if valid and port not in valid:
        errors.append(PlanError(
            code=ErrorCode.INVALID_PORT,
            device=dev_name,
            message=f"Puerto '{port}' no existe en modelo {model_name}.",
            suggestion=f"Puertos válidos: {sorted(valid)}",
        ))
