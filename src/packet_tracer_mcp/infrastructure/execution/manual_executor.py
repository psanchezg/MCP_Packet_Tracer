"""
Ejecutor manual: exporta archivos para que el usuario los copie/pegue.
"""

from __future__ import annotations
from pathlib import Path
from ...domain.models.plans import TopologyPlan
from ..generator.ptbuilder_generator import generate_ptbuilder_script, generate_full_script
from ..generator.cli_config_generator import generate_all_configs
from .executor_base import ExecutorBase


class ManualExecutor(ExecutorBase):
    """Genera archivos de salida para ejecución manual."""

    def __init__(self, output_dir: str | Path = "projects"):
        self.output_dir = Path(output_dir)

    def execute(self, plan: TopologyPlan) -> dict:
        """Genera todos los archivos de la topología."""
        project_dir = self.output_dir / plan.name.replace(" ", "_")
        project_dir.mkdir(parents=True, exist_ok=True)

        files: dict[str, str] = {}

        # PTBuilder script
        script = generate_ptbuilder_script(plan)
        script_path = project_dir / "topology.js"
        script_path.write_text(script, encoding="utf-8")
        files["topology_script"] = str(script_path)

        # Full script (topology + configs as comments)
        full = generate_full_script(plan)
        full_path = project_dir / "full_build.js"
        full_path.write_text(full, encoding="utf-8")
        files["full_script"] = str(full_path)

        # CLI configs individuales
        configs = generate_all_configs(plan)
        for device_name, config_text in configs.items():
            cfg_path = project_dir / f"{device_name}_config.txt"
            cfg_path.write_text(config_text, encoding="utf-8")
            files[f"config_{device_name}"] = str(cfg_path)

        # Plan JSON
        import json
        plan_path = project_dir / "plan.json"
        plan_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
        files["plan_json"] = str(plan_path)

        return {
            "status": "exported",
            "project_dir": str(project_dir),
            "files": files,
            "devices_count": len(plan.devices),
            "links_count": len(plan.links),
        }

    def is_available(self) -> bool:
        return True
