# Packet Tracer MCP v0.2

Servidor MCP (Model Context Protocol) que permite a un LLM **crear, configurar, validar y explicar topologías de red** en Cisco Packet Tracer.

## Arquitectura V2

```
Usuario (lenguaje natural)
    ↓
LLM (Claude, GPT, etc.)
    ↓
MCP Server (14 tools, 5 resources)
    ↓
┌──────────────────────────────────────────┐
│  adapters/mcp/      ← tools + resources  │
│  application/       ← use cases + DTOs   │
│  domain/            ← modelos + servicios│
│    ├─ models/       ← requests, plans    │
│    ├─ services/     ← orchestrator, etc. │
│    └─ rules/        ← validación         │
│  infrastructure/    ← catálogo, generators│
│    ├─ catalog/      ← dispositivos, cables│
│    ├─ generator/    ← PTBuilder + CLI    │
│    ├─ execution/    ← exportación        │
│    └─ persistence/  ← proyectos          │
│  shared/            ← enums, constants   │
└──────────────────────────────────────────┘
    ↓
Packet Tracer (via PTBuilder extension)
```

## Tools MCP (14)

| Tool | Descripción |
|---|---|
| `pt_list_devices` | Lista dispositivos disponibles con puertos |
| `pt_list_templates` | Lista plantillas de topología |
| `pt_get_device_details` | Detalles de un modelo específico |
| `pt_estimate_plan` | Estimación dry-run (sin generar plan) |
| `pt_plan_topology` | Genera plan completo desde parámetros |
| `pt_validate_plan` | Valida un plan con errores tipificados |
| `pt_fix_plan` | Auto-corrige errores del plan |
| `pt_explain_plan` | Explica decisiones en lenguaje natural |
| `pt_generate_script` | Genera script PTBuilder (.js) |
| `pt_generate_configs` | Genera configs CLI por dispositivo |
| `pt_full_build` | Pipeline completo de una sola vez |
| `pt_export` | Exporta a archivos |
| `pt_list_projects` | Lista proyectos guardados |
| `pt_load_project` | Carga un proyecto guardado |

## Resources MCP (5)

| URI | Contenido |
|---|---|
| `pt://catalog/devices` | Catálogo de dispositivos |
| `pt://catalog/cables` | Tipos de cable |
| `pt://catalog/aliases` | Alias de nombres |
| `pt://catalog/templates` | Plantillas con descripción |
| `pt://capabilities` | Capacidades del servidor |

## Nuevas features V2

- **Error taxonomy**: Errores tipificados con `ErrorCode`, sugerencias de fix
- **Auto-fixer**: Corrige cables, upgradea routers, reasigna puertos
- **Explainer**: Genera explicaciones humanas de cada decisión
- **Estimator**: Dry-run — muestra qué se creará sin generar
- **Templates formales**: 9 plantillas con metadata (tags, rangos, defaults)
- **Persistencia**: Guardar/cargar proyectos
- **30 tests**: Unit + integración

## Instalación

```bash
cd PACKET-TRACER
pip install -e .
```

## Uso

### Como servidor MCP (stdio)

```bash
python -m src.packet_tracer_mcp
```

### VS Code (`.vscode/mcp.json`)

```json
{
  "servers": {
    "packet-tracer": {
      "command": "python",
      "args": ["-m", "src.packet_tracer_mcp"],
      "cwd": "D:\\MCP\\PACKET-TRACER"
    }
  }
}
```

### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "packet-tracer": {
      "command": "python",
      "args": ["-m", "src.packet_tracer_mcp"],
      "cwd": "D:\\MCP\\PACKET-TRACER"
    }
  }
}
```

## Ejemplo de uso

```
→ pt_estimate_plan(routers=3, pcs_per_lan=4, has_wan=true)
→ pt_full_build(routers=3, pcs_per_lan=4, has_wan=true, dhcp=true)
→ pt_explain_plan(plan_json)
→ pt_fix_plan(plan_json)
→ pt_export(plan_json, project_name="mi_red")
```

## Tests

```bash
python -m pytest tests/ -v
```

## Para usar con PTBuilder

1. Instala PTBuilder en Packet Tracer (Builder Code Editor)
2. Genera el script con `pt_generate_script` o `pt_full_build`
3. Copia el script JS en PTBuilder y ejecútalo
4. Aplica las configs CLI en cada dispositivo
