# REPORT V2 — Packet Tracer MCP Server

> **Versión**: 0.2.0  
> **Lenguaje**: Python 3.11+  
> **Dependencias**: `mcp[cli] ≥1.0.0`, `pydantic ≥2.0.0`  
> **Entry point**: `python -m src.packet_tracer_mcp`

---

## ¿Qué es este proyecto?

Un **servidor MCP** (Model Context Protocol) que permite a cualquier LLM (Claude, GPT, Copilot…) **crear, configurar, validar, explicar y exportar topologías de red** en Cisco Packet Tracer, de forma completamente automatizada.

El flujo es:

```
Usuario (lenguaje natural)
    ↓
LLM (invoca tools MCP)
    ↓
Este servidor (planifica, valida, genera)
    ↓
Script PTBuilder (.js) + Configs CLI (.txt)
    ↓
Packet Tracer (ejecución via extensión PTBuilder)
```

---

## Arquitectura por capas

```
src/packet_tracer_mcp/
├── adapters/mcp/          ← 14 tools + 5 resources MCP
├── application/           ← 8 use cases + DTOs entrada/salida
├── domain/
│   ├── models/            ← TopologyRequest, TopologyPlan, PlanError
│   ├── services/          ← Orchestrator, IPPlanner, Validator, AutoFixer, Explainer, Estimator
│   └── rules/             ← Reglas de validación (dispositivos, cables, IPs)
├── infrastructure/
│   ├── catalog/           ← 11 dispositivos, 5 tipos de cable, 9 plantillas, 12 alias
│   ├── generator/         ← Generador PTBuilder (JS) + Generador CLI (IOS)
│   ├── execution/         ← ManualExecutor (exporta archivos)
│   └── persistence/       ← ProjectRepository (guardar/cargar proyectos)
├── shared/                ← Enums, constantes, utilidades
├── server.py              ← Entry point (registra tools + resources)
├── settings.py            ← Nombre, versión, instrucciones del servidor
└── __main__.py            ← python -m src.packet_tracer_mcp
```

---

## MCP Tools — 14 herramientas

Las tools son las funciones que el LLM puede invocar directamente.

### Consulta (3)

| Tool | Parámetros | Qué hace |
|------|-----------|----------|
| `pt_list_devices` | — | Lista los 11 modelos de dispositivos con sus puertos y los 12 alias disponibles |
| `pt_list_templates` | — | Lista las 9 plantillas de topología con descripción, rango de routers, tags |
| `pt_get_device_details` | `model_name` | Muestra puertos, velocidad y categoría de un modelo específico |

### Estimación (1)

| Tool | Parámetros | Qué hace |
|------|-----------|----------|
| `pt_estimate_plan` | `routers`, `pcs_per_lan`, `switches_per_router`, `servers`, `has_wan`, `dhcp`, `routing` | Dry-run: muestra cuántos dispositivos, enlaces, subredes y configs se generarán, más un nivel de complejidad (`simple`, `moderada`, `compleja`, `muy compleja`), **sin generar el plan real** |

### Planificación (1)

| Tool | Parámetros | Qué hace |
|------|-----------|----------|
| `pt_plan_topology` | `routers`, `pcs_per_lan`, `switches_per_router`, `servers`, `has_wan`, `dhcp`, `routing`, `router_model`, `switch_model`, `template` | Genera un **TopologyPlan completo** en JSON: dispositivos con coordenadas, enlaces con puertos, IPs asignadas, DHCP pools, rutas estáticas u OSPF, y validaciones sugeridas |

### Validación y corrección (3)

| Tool | Parámetros | Qué hace |
|------|-----------|----------|
| `pt_validate_plan` | `plan_json` | Valida el plan completo. Retorna errores tipificados con código (`DUPLICATE_DEVICE_NAME`, `INSUFFICIENT_PORTS`, etc.), mensaje, dispositivo afectado y sugerencia de fix |
| `pt_fix_plan` | `plan_json` | Intenta corregir errores **automáticamente**: cables incorrectos, routers con pocos puertos (upgrade a 2911), puertos inválidos (reasignación). Retorna el plan corregido + lista de fixes aplicados |
| `pt_explain_plan` | `plan_json` | Genera explicaciones en lenguaje natural de cada decisión: por qué /24, por qué cross, cuántos DHCP pools, etc. |

### Generación (2)

| Tool | Parámetros | Qué hace |
|------|-----------|----------|
| `pt_generate_script` | `plan_json`, `include_configs` | Genera el **script JavaScript** para PTBuilder: llamadas `addDevice()` y `addLink()`. Si `include_configs=true`, incluye las configs CLI como comentarios JS |
| `pt_generate_configs` | `plan_json` | Genera **bloques CLI (IOS)** individuales para cada router y switch: hostname, interfaces, DHCP, rutas estáticas, OSPF, `write memory`. También genera instrucciones de configuración para PCs |

### Pipeline completo (1)

| Tool | Parámetros | Qué hace |
|------|-----------|----------|
| `pt_full_build` | `routers`, `pcs_per_lan`, `switches_per_router`, `servers`, `has_wan`, `dhcp`, `routing`, `router_model`, `switch_model`, `template` | **Todo de una vez**: planifica → valida → genera script → genera configs → explica → estima. Devuelve: resumen, validación, explicación, tabla de direccionamiento, script PTBuilder, configs CLI, verificaciones sugeridas, y el plan JSON |

### Exportación y proyectos (3)

| Tool | Parámetros | Qué hace |
|------|-----------|----------|
| `pt_export` | `plan_json`, `project_name`, `output_dir` | Exporta a disco: `topology.js`, `full_build.js`, `{dispositivo}_config.txt`, `plan.json` |
| `pt_list_projects` | `output_dir` | Lista proyectos guardados con metadata (fecha, dispositivos, validez) |
| `pt_load_project` | `project_name`, `output_dir` | Carga un proyecto guardado y devuelve el plan JSON |

---

## MCP Resources — 5 recursos

Los resources son datos estáticos que el LLM puede consultar para contexto.

| URI | Contenido |
|-----|-----------|
| `pt://catalog/devices` | JSON con los 11 modelos: nombre, categoría, lista de puertos |
| `pt://catalog/cables` | JSON con los 5 tipos de cable: `straight`, `cross`, `serial`, `fiber`, `console` |
| `pt://catalog/aliases` | JSON con 12 alias: `"router"→"2911"`, `"pc"→"PC"`, `"wan"→"Cloud-PT"`, etc. |
| `pt://catalog/templates` | JSON con las 9 plantillas: nombre, key, descripción, rango de routers, tags |
| `pt://capabilities` | JSON con versión, features soportados y no soportados, límites máximos |

---

## Catálogo de dispositivos — 11 modelos

| Modelo | Categoría | Puertos |
|--------|-----------|---------|
| **1941** | Router | 2× GigabitEthernet + 2× Serial |
| **2901** | Router | 2× GigabitEthernet + 2× Serial |
| **2911** | Router | 3× GigabitEthernet + 2× Serial |
| **4321** | Router | 2× GigabitEthernet |
| **2960** | Switch | 24× FastEthernet + 2× GigabitEthernet |
| **3560** | Switch | 24× FastEthernet + 2× GigabitEthernet |
| **PC** | PC | 1× FastEthernet |
| **Server** | Server | 1× FastEthernet |
| **Laptop** | Laptop | 1× FastEthernet |
| **Cloud-PT** | Cloud | 6× FastEthernet |
| **AccessPoint-PT** | AP | 1× FastEthernet |

---

## Plantillas de topología — 9 templates

| Plantilla | Key | Routers | Descripción |
|-----------|-----|---------|-------------|
| **Single LAN** | `single_lan` | 1 | 1 router + 1 switch + PCs. La más básica |
| **Multi LAN** | `multi_lan` | 2–10 | N routers en cadena, cada uno con su LAN |
| **Multi LAN + WAN** | `multi_lan_wan` | 3–10 | Igual que multi_lan pero con Cloud WAN |
| **Star** | `star` | 1 | 1 router central con múltiples switches |
| **Hub & Spoke** | `hub_spoke` | 4–10 | 1 router hub + N routers spoke |
| **Branch Office** | `branch_office` | 3–8 | Oficina central + sucursales via WAN |
| **Router on a Stick** | `router_on_a_stick` | 1 | Inter-VLAN routing (1 router + 1 switch) |
| **Three Router Triangle** | `three_router_triangle` | 3 | 3 routers en triángulo con OSPF |
| **Custom** | `custom` | 1–20 | Topología libre |

---

## Sistema de errores — 15 códigos tipificados

Cada error tiene: `code`, `message`, `device` (afectado), `suggestion` (cómo arreglarlo).

| Categoría | Código | Descripción |
|-----------|--------|-------------|
| **Dispositivo** | `UNKNOWN_DEVICE_MODEL` | Modelo no existe en catálogo |
| | `DUPLICATE_DEVICE_NAME` | Dos dispositivos con el mismo nombre |
| | `INSUFFICIENT_PORTS` | Modelo no tiene suficientes puertos para los enlaces |
| **Enlace** | `DEVICE_NOT_FOUND` | Enlace referencia un dispositivo que no existe |
| | `INVALID_PORT` | Puerto no existe en el modelo |
| | `PORT_ALREADY_USED` | Puerto ya está conectado a otro enlace |
| | `INVALID_CABLE_TYPE` | Tipo de cable incorrecto para esa combinación |
| **IP** | `INVALID_IP_ADDRESS` | Formato de IP inválido |
| | `SUBNET_OVERLAP` | Subredes se solapan |
| | `IP_CONFLICT` | Misma IP en dos dispositivos |
| **DHCP** | `DHCP_ROUTER_NOT_FOUND` | Pool apunta a un router inexistente |
| | `DHCP_GATEWAY_MISMATCH` | Gateway del pool no coincide con interface del router |
| **Routing** | `UNSUPPORTED_ROUTING_PROTOCOL` | EIGRP/RIP no soportados aún |
| **Template** | `TEMPLATE_CONSTRAINT_VIOLATION` | Parámetros fuera del rango de la plantilla |
| **General** | `INVALID_INTERFACE_ASSIGNMENT` | Interface mal asignada |

---

## Auto-Fixer — correcciones automáticas

El auto-fixer intenta resolver 3 tipos de problemas sin intervención:

1. **Cables incorrectos**: Si un enlace router↔router tiene cable `straight`, lo cambia a `cross`
2. **Puertos insuficientes**: Si un router 1941 (2 GigE) necesita 3 enlaces, lo upgradea a 2911 (3 GigE)
3. **Puertos inválidos**: Si un enlace apunta a `FastEthernet0/5` en un router que no lo tiene, lo reasigna al primer puerto disponible

---

## Explainer — explicaciones generadas

Genera una lista de explicaciones en español sobre el plan:

- "Topología con 3 router(s), 3 switch(es), 6 PC(s) y conexión WAN"
- "Se asignaron 3 subredes /24 para LANs — cada LAN soporta hasta 254 hosts"
- "Los enlaces entre routers usan subredes /30 (punto a punto)"
- "Se usan 2 cable(s) cruzado(s) entre dispositivos del mismo tipo"
- "Se configuraron 3 pool(s) DHCP — los PCs obtienen IP automáticamente"
- "Se configuraron 4 ruta(s) estática(s)"
- "Verificaciones sugeridas: ping PC1 → PC6"

---

## Estimator — estimación dry-run

Sin generar un plan completo, calcula:

```json
{
  "devices": { "routers": 3, "switches": 3, "pcs": 6, "servers": 0, "clouds": 1, "total": 13 },
  "links": { "router_to_router": 2, "router_to_switch": 3, "switch_to_pc": 6, "total": 12 },
  "configs": { "routers_to_configure": 3, "dhcp_pools": 3, "static_routes": 4 },
  "subnets": { "lan_subnets": 3, "link_subnets": 3 },
  "complexity": "moderada"
}
```

---

## Generador PTBuilder — salida JavaScript

Genera scripts compatibles con la extensión **Builder Code Editor** de Packet Tracer:

```javascript
// --- Dispositivos ---
addDevice("R1", "2911", 100, 100);
addDevice("SW1", "2960", 100, 250);
addDevice("PC1", "PC", 20, 400);

// --- Enlaces ---
addLink("R1", "GigabitEthernet0/1", "SW1", "FastEthernet0/1", "straight");
addLink("SW1", "FastEthernet0/2", "PC1", "FastEthernet0", "straight");
```

---

## Generador CLI — configuraciones IOS

Genera bloques de configuración listos para pegar en cada dispositivo:

**Router:**
```
enable
configure terminal
hostname R1
no ip domain-lookup

interface GigabitEthernet0/1
 ip address 192.168.0.1 255.255.255.0
 no shutdown
 exit

ip dhcp excluded-address 192.168.0.1 192.168.0.1
ip dhcp pool LAN_R1_0
 network 192.168.0.0 255.255.255.0
 default-router 192.168.0.1
 dns-server 8.8.8.8
 exit

ip route 192.168.1.0 255.255.255.0 10.0.0.2
end
write memory
```

**Switch:**
```
enable
configure terminal
hostname SW1
end
write memory
```

**PC (instrucciones):**
```
IP Address: DHCP
Default Gateway: 192.168.0.1
DNS Server: 8.8.8.8
```

---

## IP Planner — direccionamiento automático

| Tipo | Rango base | Prefijo | Ejemplo |
|------|-----------|---------|---------|
| **LANs** | `192.168.0.0/16` | /24 (254 hosts) | `192.168.0.0/24`, `192.168.1.0/24`, … |
| **Links inter-router** | `10.0.0.0/16` | /30 (2 hosts) | `10.0.0.0/30`, `10.0.0.4/30`, … |

El gateway de cada LAN es siempre `.1` (primera IP útil). Los PCs reciben IPs secuenciales desde `.2`.

---

## Routing soportado

| Protocolo | Estado | Qué genera |
|-----------|--------|------------|
| **static** | ✅ Completo | `ip route` por cada subred remota |
| **ospf** | ✅ Completo | `router ospf 1` + `network` wildcard statements |
| **eigrp** | ❌ Pendiente | Solo se declara en enum |
| **rip** | ❌ Pendiente | Solo se declara en enum |
| **none** | ✅ | No genera rutas |

---

## Exportación a disco

`pt_export` genera un directorio de proyecto con:

```
projects/mi_topologia/
├── topology.js          ← Script PTBuilder (solo addDevice + addLink)
├── full_build.js        ← Script PTBuilder + configs como comentarios
├── plan.json            ← Plan completo en JSON (recargable)
├── metadata.json        ← Fecha, cantidad de dispositivos, estado de validación
├── R1_config.txt        ← Config CLI del router R1
├── R2_config.txt        ← Config CLI del router R2
├── SW1_config.txt       ← Config CLI del switch SW1
└── ...
```

---

## Persistencia de proyectos

| Operación | Qué hace |
|-----------|----------|
| `pt_export` | Guarda plan + scripts + configs en un directorio |
| `pt_list_projects` | Lista todos los proyectos guardados con su metadata |
| `pt_load_project` | Recarga un plan JSON guardado (para modificar, re-validar, re-exportar) |

---

## Tests — 30 tests, 7 archivos

| Archivo | Tests | Qué cubre |
|---------|-------|-----------|
| `test_ip_planner.py` | 6 | Subredes LAN, subredes link, hosts, gateways, asignación secuencial |
| `test_validator.py` | 4 | Plan válido, nombres duplicados, modelos inválidos, enlaces a dispositivos fantasma |
| `test_auto_fixer.py` | 2 | Corrección de cables, escenario sin correcciones |
| `test_explainer.py` | 3 | Explicación básica, DHCP, WAN |
| `test_estimator.py` | 4 | Estimación básica, clouds WAN, niveles de complejidad |
| `test_generators.py` | 4 | `addDevice()`, `addLink()`, hostname en config, DHCP en config |
| `test_full_build.py` | 7 | 2 routers, 3 routers+WAN, OSPF, 1 router, sin DHCP, con servers, campos de estimación |

```bash
python -m pytest tests/ -v    # 30 passed in 0.12s
```

---

## Configuración del servidor

### VS Code (`.vscode/mcp.json`)
```json
{
  "servers": {
    "packet-tracer": {
      "command": "python",
      "args": ["-m", "src.packet_tracer_mcp"],
      "cwd": "."
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

---

## Capacidades declaradas

```json
{
  "version": "0.2.0",
  "routing": ["static", "ospf"],
  "features": ["dhcp", "wan", "switching", "auto_fix", "explain", "dry_run"],
  "unsupported": ["nat", "acl", "eigrp", "vlan", "stp"],
  "max_routers": 20,
  "max_pcs_per_lan": 24,
  "max_switches_per_router": 4
}
```

---

## Flujo recomendado de uso

```
1.  pt_list_devices          → ver qué hay disponible
2.  pt_list_templates        → elegir plantilla
3.  pt_estimate_plan(...)    → ver qué se va a crear (dry-run)
4.  pt_plan_topology(...)    → generar el plan completo
5.  pt_validate_plan(json)   → verificar que no tenga errores
6.  pt_fix_plan(json)        → corregir errores automáticamente (si hay)
7.  pt_explain_plan(json)    → entender las decisiones
8.  pt_generate_script(json) → obtener el JS para PTBuilder
9.  pt_generate_configs(json)→ obtener las configs CLI
10. pt_export(json)          → guardar todo a disco

— o directamente —

1.  pt_full_build(...)       → todo de una sola vez
2.  pt_export(json)          → guardar a disco
```
