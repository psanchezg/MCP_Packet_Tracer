"""Reglas de validacion de dispositivos."""

from __future__ import annotations

from ...infrastructure.catalog.devices import resolve_model
from ..models.errors import ErrorCode, PlanError
from ..models.plans import TopologyPlan


def validate_devices(plan: TopologyPlan) -> list[PlanError]:
    """Valida que todos los dispositivos sean validos."""
    errors: list[PlanError] = []
    names_seen: set[str] = set()

    for dev in plan.devices:
        if dev.name in names_seen:
            errors.append(
                PlanError(
                    code=ErrorCode.DUPLICATE_DEVICE_NAME,
                    device=dev.name,
                    message=f"Nombre de dispositivo duplicado: '{dev.name}'",
                    suggestion="Renombrar uno de los dispositivos duplicados.",
                )
            )
        names_seen.add(dev.name)

        model = resolve_model(dev.model)
        if model is None:
            errors.append(
                PlanError(
                    code=ErrorCode.UNKNOWN_DEVICE_MODEL,
                    device=dev.name,
                    message=f"Modelo desconocido '{dev.model}'.",
                    suggestion=(
                        "Usa pt_list_devices para ver el catalogo completo de modelos "
                        "soportados y sus puertos."
                    ),
                )
            )

    return errors
