# MCP Packet Tracer - Guia de Configuracion

Controla Cisco Packet Tracer desde Claude Code, VS Code Copilot o Codex CLI usando lenguaje natural.

## Requisitos

- Cisco Packet Tracer 8.2+
- Python 3.11+
- Claude Code, VS Code con Copilot, Claude Desktop, o Codex CLI

## 1. Instalar el MCP Server

### Opción A: Usando pip (estándar)

```bash
cd ruta/al/proyecto
pip install -e .
```

Para desarrollo (incluye pytest, ruff, mypy):

```bash
pip install -e ".[dev]"
```

### Opción B: Usando uv (rápido)

```bash
cd ruta/al/proyecto
uv venv
uv pip install -e .
```

Para desarrollo con uv:

```bash
uv pip install -e ".[dev]"
```

Nota: [uv](https://docs.astral.sh/uv/) es un gestor de paquetes de Python más rápido. Para instalarlo:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh  # Linux/Mac
```

## 2. Instalar PTBuilder en Packet Tracer

PTBuilder es la extension que permite ejecutar comandos JavaScript en Packet Tracer.

1. Abre Packet Tracer
2. Ve a **Extensions > Scripting > Configure PT Script Modules**
3. Click en **Add...**
4. Navega a `<ruta/al/proyecto>/PTBuilder/Builder.pts` y abrelo
5. Selecciona MCP-BUILDER en la lista y dale **Start**

## 3. Configurar el Bridge (una sola vez)
(no necesario)
El bridge permite que el MCP server envie comandos en tiempo real a Packet Tracer. Hay que agregar el polling directamente en PTBuilder:

1. En Packet Tracer, ve a **Extensions > Scripting > Configure PT Script Modules**
2. Selecciona **Builder** y click en **Edit** (o doble click)
3. Ve a la pestana **Custom Interfaces**
4. Selecciona el archivo **interface.js**
5. Agrega este codigo **al final** del archivo:

```javascript
// MCP Bridge: consulta periodicamente el backend para ejecutar codigo
setInterval(function() {
    var x = new XMLHttpRequest();
    x.open("GET", "http://127.0.0.1:54321/next", true);
    x.timeout = 1000;

    x.onload = function() {
        if (x.status === 200 && x.responseText) {
            var cmd = x.responseText;
            var preview = cmd.substring(0, 120);
            log("Received from MCP: " + preview + (cmd.length > 120 ? "..." : ""), "recv");

            try {
                $se("runCode", cmd);
                state.commandCount++;
                log("Command executed successfully", "ok");
            } catch(e) {
                log("Command execution failed: " + e.message, "err");
            }
        }
    };

    x.onerror = x.ontimeout = function() {};
    x.send();
}, 500);
```

6. Cierra el editor de scripting
7. **Stop** y **Start** el modulo Builder desde Configure PT Script Modules

## 4. Configurar tu cliente AI

### Claude Code

Crear `.mcp.json` en la raiz del proyecto:

```json
{
  "mcpServers": {
    "packet-tracer": {
      "type": "http",
      "url": "http://127.0.0.1:39000/mcp"
    }
  }
}
```

O global en `~/.claude/.mcp.json` con el mismo contenido.

### VS Code (Copilot)

Crear `.vscode/mcp.json` en tu proyecto:

```json
{
  "servers": {
    "packet-tracer": {
      "url": "http://127.0.0.1:39000/mcp"
    }
  }
}
```

### Claude Desktop

Agregar en `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "packet-tracer": {
      "url": "http://127.0.0.1:39000/mcp"
    }
  }
}
```

### Codex CLI (OpenAI)

Agregar en `~/.codex/config.toml`:

```toml
[mcp_servers.packet-tracer]
type = "url"
url = "http://127.0.0.1:39000/mcp"
```

## 5. Uso diario

Cada vez que quieras usar el sistema:

### Paso 1 - Levantar el MCP server

Abre una terminal y ejecuta:

**Con pip (estándar):**

```bash
python -m src.packet_tracer_mcp
```

**Con uv (desde el entorno virtual):**

```bash
# Activar el entorno virtual
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows
python -m src.packet_tracer_mcp
```

O directamente con uv run:
```bash
uv run python -m src.packet_tracer_mcp
```

Deberia mostrar:
```
INFO: Uvicorn running on http://127.0.0.1:39000 (Press CTRL+C to quit)
```

Para cambiar el puerto: `PT_MCP_PORT=8080 python -m src.packet_tracer_mcp`

Para debug: `PT_MCP_LOG_LEVEL=DEBUG python -m src.packet_tracer_mcp`

### Paso 2 - Preparar Packet Tracer

1. Abre Packet Tracer
2. Verifica que MCP-BUILDER este en **Start** (Extensions > Scripting > Configure PT Script Modules)
3. Abre **Extensions > Builder Code Editor**
4. Pega el siguiente bootstrap script en el Code Editor y dale **Run**:

```javascript
/* PT-MCP Bridge */ window.webview.evaluateJavaScriptAsync("setInterval(function(){var x=new
  XMLHttpRequest();x.open('GET','http://127.0.0.1:54321/next',true);x.onload=function(){if(x.status===
  200&&x.responseText){$se('runCode',x.responseText)}};x.onerror=function(){};x.send()},500)");
```

Esto inicia el polling que conecta Packet Tracer con el bridge HTTP. Mientras el Code Editor este abierto, PT escuchara comandos del MCP server cada 500ms.

> **Nota:** Si ya configuraste el bridge en el Paso 3 de la instalacion (editando `interface.js`), este paso no es necesario — el polling arranca automaticamente al abrir el Builder Code Editor.

### Paso 3 - Verificar la conexion

Usa la herramienta `pt_ping_bridge` para confirmar que todo esta conectado:

```
bridge_up: true
pt_connected: true
url: http://127.0.0.1:54321
```

Si `pt_connected` es `false`, revisa que el bootstrap este corriendo en el Code Editor.

### Paso 4 - Usar tu cliente AI

Abre Claude Code, VS Code, Claude Desktop, o Codex CLI y empieza a pedir topologias:

```
"Creame una topologia con 2 routers y 3 PCs"
"Haz una red con 3 routers en triangulo con OSPF"
"Agrega un servidor a la red"
"Configurame EIGRP entre R1 y R2"
"Genera documentacion de la topologia"
```

## Herramientas MCP disponibles (35)

### Catalogo y exploracion

| Herramienta | Descripcion |
|---|---|
| `pt_list_devices` | Lista los 19 modelos de dispositivos disponibles |
| `pt_list_templates` | Lista plantillas de topologia (single_lan, star, branch, etc.) |
| `pt_get_device_details` | Detalles de un modelo (puertos, categoria) |

### Planificacion y estimacion

| Herramienta | Descripcion |
|---|---|
| `pt_estimate_plan` | Dry-run: estima recursos sin generar plan completo |
| `pt_plan_topology` | Genera un plan completo desde parametros |

### Validacion

| Herramienta | Descripcion |
|---|---|
| `pt_validate_plan` | Valida un plan contra 15 tipos de errores |
| `pt_fix_plan` | Auto-corrige errores (cables, puertos, modelos) |
| `pt_explain_plan` | Explica el plan en lenguaje natural |
| `pt_validate_config` | Valida configuracion CLI de un dispositivo (IPs duplicadas, ACLs, etc.) |
| `pt_validate_topology` | Validacion profunda (dispositivos huerfanos, subnets, etc.) |

### Generacion

| Herramienta | Descripcion |
|---|---|
| `pt_generate_script` | Genera script JavaScript para PTBuilder |
| `pt_generate_configs` | Genera configuraciones CLI por dispositivo |
| `pt_full_build` | Pipeline completo: plan + validacion + script + configs |

### Deploy y bridge

| Herramienta | Descripcion |
|---|---|
| `pt_deploy` | Exporta y copia script al clipboard |
| `pt_live_deploy` | Envia comandos en tiempo real a PT via bridge |
| `pt_bridge_status` | Verifica conexion con PT |
| `pt_ping_bridge` | Health check detallado (bridge_up, pt_connected, url) |

### Recuperacion

| Herramienta | Descripcion |
|---|---|
| `pt_undo_last_action` | Deshace el ultimo comando (addDevice → deleteDevice) |
| `pt_load_last_plan` | Recupera el ultimo plan desplegado desde disco |

### Interaccion con topologia en vivo

| Herramienta | Descripcion |
|---|---|
| `pt_query_topology` | Lista dispositivos actuales en PT |
| `pt_delete_device` | Elimina un dispositivo del canvas |
| `pt_rename_device` | Renombra un dispositivo |
| `pt_move_device` | Mueve un dispositivo a nuevas coordenadas |
| `pt_delete_link` | Elimina un enlace por dispositivo/interfaz |
| `pt_send_raw` | Ejecuta JavaScript arbitrario en PT |

### Inteligencia de topologia

| Herramienta | Descripcion |
|---|---|
| `pt_analyze_topology` | Analiza una descripcion de red en texto natural (NLP) |
| `pt_suggest_improvements` | Sugiere mejoras para un plan existente |
| `pt_calculate_addressing` | Calcula direccionamiento IPv4/IPv6 dual-stack |

### Templates de configuracion (Jinja2)

| Herramienta | Descripcion |
|---|---|
| `pt_list_config_templates` | Lista las 8 plantillas IOS disponibles |
| `pt_apply_template` | Renderiza una plantilla (OSPF, EIGRP, VLAN, HSRP, NAT, ACL, DHCP, STP) |

### Presets de escenarios

| Herramienta | Descripcion |
|---|---|
| `pt_list_presets` | Lista los 8 presets (small_office, branch_hq, ccna_lab, etc.) |
| `pt_load_preset` | Carga un preset y genera el plan completo |

### Exportacion y proyectos

| Herramienta | Descripcion |
|---|---|
| `pt_export` | Exporta plan a archivos (JS, CLI configs, JSON) |
| `pt_list_projects` | Lista proyectos guardados |
| `pt_load_project` | Carga un proyecto guardado |
| `pt_export_documentation` | Genera documentacion completa (tabla de IPs, configs, verificacion) |

## Recursos MCP (6)

| Recurso | Descripcion |
|---|---|
| `pt://catalog/devices` | Catalogo de 19 modelos con puertos |
| `pt://catalog/cables` | Tipos de cable (straight, cross, serial, fiber) |
| `pt://catalog/aliases` | 52 alias de modelos (firewall→ASA5506, etc.) |
| `pt://catalog/templates` | Plantillas de topologia |
| `pt://capabilities` | Version, features, limites del servidor |
| `pt://prompts/ptbuilder-guide` | Guia completa para generar scripts PTBuilder |

## API de PTBuilder (importante)

PTBuilder expone **exactamente 3 funciones JavaScript**. El MCP server genera codigo que usa unicamente estas:

```javascript
// Crear un dispositivo en el canvas
addDevice("R1", "2911", 400, 300);

// Crear un enlace entre dos dispositivos
addLink("R1", "GigabitEthernet0/0", "SW1", "GigabitEthernet0/1", "straight");

// Configurar un dispositivo con comandos IOS CLI (sin enable/configure terminal)
configureDevice("R1", [
    "hostname R1",
    "interface GigabitEthernet0/0",
    "ip address 192.168.1.1 255.255.255.0",
    "no shutdown"
]);
```

**No existen** otras funciones como `configureIosDevice()`, `configurePcIp()`, `createNetwork()`, etc. Si ves errores de "function not defined", verifica que el MCP server este actualizado.

## Modelos de dispositivos soportados (19)

| Categoria | Modelos |
|---|---|
| Routers | 1941, 2901, 2911, ISR4321, ISR4331 |
| L3 Switches | 3650-24PS, 3850-24T |
| L2 Switches | 2960-24TT, 2960-48TT, 3560-24PS |
| Firewall | ASA5506 |
| End Devices | PC-PT, Server-PT, Laptop-PT, Tablet-PT |
| WAN | Cloud-PT, DSL-Modem-PT |
| Wireless | AccessPoint-PT, WRT300N |

## Protocolos de ruteo soportados

| Protocolo | Descripcion |
|---|---|
| `static` | Rutas estaticas con soporte de floating routes (AD=254) |
| `ospf` | OSPF con router-id y soporte multi-area |
| `rip` | RIP v2 con no auto-summary |
| `eigrp` | EIGRP con wildcard masks y AS configurable |
| `none` | Sin ruteo |

## Solucion de problemas

### "Bridge activo pero PT NO esta conectado"

- Verifica que el Builder Code Editor este abierto en PT
- Haz Stop/Start del modulo Builder
- Vuelve a abrir Extensions > Builder Code Editor
- Ejecuta `pt_ping_bridge` para ver el estado detallado

### "Error: puerto 39000 en uso"

- Packet Tracer usa el puerto 39000 para IPC por defecto
- Cambia el puerto: `PT_MCP_PORT=8080 python -m src.packet_tracer_mcp`

### "function not defined" en Packet Tracer

- El MCP server genera solo `addDevice()`, `addLink()`, `configureDevice()`
- Si ves errores con otras funciones, actualiza el MCP server: `pip install -e .`
- Funciones como `queryTopology`, `deleteDevice` funcionan solo via bridge (no en scripts directos)

### Tests no pasan

```bash
# Instalar dependencias de desarrollo
pip install -e ".[dev]"

# Correr 129 tests
python -m pytest tests/ -v

# Con cobertura
python -m pytest tests/ --cov=src/packet_tracer_mcp --cov-report=term-missing
```

## Arquitectura

```
Cliente AI (Claude/Copilot/Codex)
        |
        | MCP over HTTP (puerto 39000)
        v
   MCP Server (Python, 35 tools, 6 resources)
        |
        | HTTP (puerto 54321)
        v
   Bridge HTTP (auto-start)
        |
        | Polling cada 500ms (GET /next)
        v
   PTBuilder (QWebEngine webview)
        |
        | $se('runCode', cmd)
        v
   PT Script Engine → Cisco Packet Tracer
```

El bridge HTTP se inicia automaticamente cuando el MCP server arranca. Solo necesitas asegurarte de que el bootstrap este corriendo en el Builder Code Editor (o que `interface.js` tenga el polling configurado).
