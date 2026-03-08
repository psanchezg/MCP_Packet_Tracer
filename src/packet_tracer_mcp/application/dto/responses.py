"""DTOs de respuesta para la capa de aplicación."""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class BuildResponse:
    """Respuesta del full build."""
    plan_json: str
    script: str
    configs: dict[str, str]
    validation: dict
    explanation: list[str]
    estimation: dict
    is_valid: bool
    errors: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)


@dataclass
class ValidationResponse:
    """Respuesta de validación."""
    is_valid: bool
    errors: list[dict]
    warnings: list[dict]


@dataclass
class FixResponse:
    """Respuesta de fix."""
    plan_json: str
    fixes_applied: list[str]
    is_valid: bool
    remaining_errors: list[dict]


@dataclass
class ExportResponse:
    """Respuesta de exportación."""
    status: str
    project_dir: str
    files: dict[str, str]
