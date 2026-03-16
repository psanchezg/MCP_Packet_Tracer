"""Bridge tools — live deploy, bridge status, ping, undo, topology."""

from __future__ import annotations

import json
import time

from mcp.server.fastmcp import FastMCP

from ....domain.models.plans import TopologyPlan
from ....infrastructure.generator.ptbuilder_generator import generate_executable_script
from ....shared.logging import get_logger
from ._bridge_helpers import (
    _extract_ptbuilder_calls,
    bridge_pt_connected,
    bridge_send_and_wait,
    check_bridge,
    clear_command_history,
    ensure_bridge,
    get_bootstrap,
    get_bridge_url,
    http_post,
    js_escape,
    load_last_plan,
    ping_bridge,
    pop_last_command,
    record_command,
    save_last_plan,
)

logger = get_logger(__name__)


def register_bridge_tools(mcp: FastMCP) -> None:
    """Register bridge and topology interaction MCP tools."""
    # Start bridge immediately on registration
    ensure_bridge()

    @mcp.tool()
    def pt_live_deploy(
        plan_json: str,
        command_delay: float = 1.0,
    ) -> str:
        """
        Send commands directly to Packet Tracer in real time.

        The HTTP bridge starts automatically inside the MCP server.
        Just make sure the bootstrap is running in Builder Code Editor.

        Parameters:
        - plan_json: Plan JSON (output of pt_plan_topology or pt_full_build)
        - command_delay: delay between commands in seconds (default 1.0)
        """
        if not ensure_bridge():
            return (
                "Could not start HTTP bridge on :54321.\n"
                "Port blocked by another process. Free the port and try again."
            )

        if not bridge_pt_connected():
            return (
                "Bridge active at http://127.0.0.1:54321 but PT is NOT connected.\n\n"
                "Paste this in Builder Code Editor (Extensions > Builder Code Editor) "
                "and click Run:\n\n"
                + get_bootstrap()
                + "\n\nThen call pt_live_deploy again.\n\n"
                "IMPORTANT: XMLHttpRequest does NOT exist in PT's Script Engine.\n"
                "The bootstrap injects a polling loop in the webview (QWebEngine) "
                "which DOES have XMLHttpRequest."
            )

        logger.info("pt_live_deploy: deploying topology")
        plan = TopologyPlan.model_validate_json(plan_json)
        script = generate_executable_script(plan)
        commands = _extract_ptbuilder_calls(script)
        logger.debug(
            "pt_live_deploy: extracted %d complete PT calls from script",
            len(commands),
        )

        sent = 0
        bridge_url = get_bridge_url()
        clear_command_history()
        for cmd in commands:
            status, _ = http_post(f"{bridge_url}/queue", cmd)
            if status == 200:
                sent += 1
                record_command(cmd)
            time.sleep(command_delay)

        # Persist plan for recovery
        save_last_plan(plan_json)

        logger.info("pt_live_deploy: sent %d commands", sent)
        failed = len(commands) - sent
        status_line = (
            "Topology deployed to Packet Tracer!"
            if failed == 0
            else f"Deployed with {failed} queuing error(s) — check logs."
        )
        return (
            f"{status_line}\n"
            f"  Commands extracted : {len(commands)}\n"
            f"  Commands sent      : {sent}\n"
            f"  Queuing errors     : {failed}\n"
            f"  Devices            : {len(plan.devices)}\n"
            f"  Links              : {len(plan.links)}"
        )

    @mcp.tool()
    def pt_bridge_status() -> str:
        """
        Check HTTP bridge status with Packet Tracer.
        The bridge starts automatically if not running.
        """
        if not ensure_bridge():
            return (
                "Could not start HTTP bridge on :54321.\n"
                "Port blocked by another process. Free the port and try again."
            )

        if bridge_pt_connected():
            return (
                "Bridge ACTIVE and CONNECTED. "
                "Packet Tracer is receiving commands at http://127.0.0.1:54321"
            )

        return (
            "Bridge active at http://127.0.0.1:54321 but PT is NOT connected.\n\n"
            "Paste this in Builder Code Editor (Extensions > Builder Code Editor) "
            "and click Run:\n\n"
            + get_bootstrap()
        )

    @mcp.tool()
    def pt_ping_bridge() -> str:
        """
        Health check for the bridge and Packet Tracer connectivity.
        Returns detailed status: bridge_up, pt_connected, url.
        """
        health = ping_bridge()
        return json.dumps(health, indent=2)

    @mcp.tool()
    def pt_undo_last_action() -> str:
        """
        Attempt to undo the last command sent to Packet Tracer.

        For addDevice commands, sends a corresponding deleteDevice.
        For addLink commands, cannot be undone individually.
        For other commands, reports what was last sent.
        """
        err = check_bridge()
        if err:
            return err

        cmd = pop_last_command()
        if not cmd:
            return "No commands to undo."

        # Try to parse addDevice calls and reverse them
        if cmd.startswith("addDevice("):
            # Parse: addDevice("name", "model", x, y)
            try:
                inner = cmd[len("addDevice("):]
                if inner.endswith(");"):
                    inner = inner[:-2]
                elif inner.endswith(")"):
                    inner = inner[:-1]
                parts = inner.split(",")
                dev_name = parts[0].strip().strip('"').strip("'")
                js = f'deleteDevice("{js_escape(dev_name)}")'
                result = bridge_send_and_wait(js, timeout=8.0)
                if result:
                    data = json.loads(result)
                    if data.get("success"):
                        return f"Undone: deleted device '{dev_name}'"
                return f"Undo attempted for addDevice('{dev_name}'). Check PT."
            except Exception:
                return f"Could not parse command for undo: {cmd}"

        return f"Last command was: {cmd[:100]}... (manual undo required)"

    @mcp.tool()
    def pt_load_last_plan() -> str:
        """
        Load the last successfully deployed plan from disk.
        Useful for recovery after server restarts.
        """
        plan_json = load_last_plan()
        if not plan_json:
            return "No persisted plan found."
        return plan_json

    # ------------------------------------------------------------------
    # Topology interaction tools (send command -> wait for result)
    # ------------------------------------------------------------------

    @mcp.tool()
    def pt_query_topology() -> str:
        """
        Query what devices currently exist in Packet Tracer.
        Returns name, type, and model of each device in the active topology.
        Requires connected bridge (use pt_bridge_status to check).
        """
        err = check_bridge()
        if err:
            return err

        result = bridge_send_and_wait("queryTopology()", timeout=10.0)
        if result is None:
            return "No response from PT (timeout). Verify the bootstrap is running."
        try:
            data = json.loads(result)
        except Exception:
            return f"Unexpected response from PT: {result}"

        devices = data.get("devices", [])
        if not devices:
            return "No devices in current topology."

        type_labels = {
            0: "Router", 1: "Switch", 7: "AccessPoint", 8: "PC",
            9: "Server", 16: "L3 Switch", 17: "Laptop", 18: "Tablet",
        }
        lines = [f"Devices in Packet Tracer ({data.get('count', len(devices))}):", ""]
        for d in devices:
            tname = d.get("typeName") or type_labels.get(d.get("type"), f"type={d.get('type')}")
            model = f" [{d['model']}]" if d.get("model") else ""
            pos = f"  pos=({d['x']},{d['y']})" if d.get("x") is not None else ""
            lines.append(f"  {d['name']:15}  {tname}{model}{pos}")
        return "\n".join(lines)

    @mcp.tool()
    def pt_delete_device(device_name: str) -> str:
        """
        Delete a device from the active Packet Tracer topology.

        Parameters:
        - device_name: exact device name (e.g. "R1", "PC3")
        """
        err = check_bridge()
        if err:
            return err

        safe_name = js_escape(device_name)
        js = f'deleteDevice("{safe_name}")'
        result = bridge_send_and_wait(js, timeout=8.0)
        if result is None:
            return f"No response from PT. Device '{device_name}' may not exist."
        try:
            data = json.loads(result)
            if data.get("success"):
                record_command(f'deleteDevice("{safe_name}")')
                return f"Device '{device_name}' deleted successfully."
            return f"Error deleting '{device_name}': {data.get('error', 'unknown')}"
        except Exception:
            return f"Unexpected response: {result}"

    @mcp.tool()
    def pt_rename_device(old_name: str, new_name: str) -> str:
        """
        Rename a device in the active Packet Tracer topology.

        Parameters:
        - old_name: current device name
        - new_name: new name
        """
        err = check_bridge()
        if err:
            return err

        safe_old = js_escape(old_name)
        safe_new = js_escape(new_name)
        js = f'renameDevice("{safe_old}", "{safe_new}")'
        result = bridge_send_and_wait(js, timeout=8.0)
        if result is None:
            return "No response from PT."
        try:
            data = json.loads(result)
            if data.get("success"):
                return f"Device renamed: '{old_name}' -> '{new_name}'"
            return f"Error: {data.get('error', 'unknown')}"
        except Exception:
            return f"Unexpected response: {result}"

    @mcp.tool()
    def pt_move_device(device_name: str, x: int, y: int) -> str:
        """
        Move a device to new coordinates on the Packet Tracer canvas.

        Parameters:
        - device_name: device name
        - x: X coordinate (e.g. 100-800)
        - y: Y coordinate (e.g. 100-600)
        """
        err = check_bridge()
        if err:
            return err

        safe_name = js_escape(device_name)
        js = f'moveDevice("{safe_name}", {int(x)}, {int(y)})'
        result = bridge_send_and_wait(js, timeout=8.0)
        if result is None:
            return "No response from PT."
        try:
            data = json.loads(result)
            if data.get("success"):
                return f"Device '{device_name}' moved to ({x}, {y})."
            return f"Error: {data.get('error', 'unknown')}"
        except Exception:
            return f"Unexpected response: {result}"

    @mcp.tool()
    def pt_delete_link(device_name: str, interface_name: str) -> str:
        """
        Delete the link connected to a specific interface on a device.

        Parameters:
        - device_name: device name (e.g. "R1")
        - interface_name: interface name (e.g. "GigabitEthernet0/0")
        """
        err = check_bridge()
        if err:
            return err

        safe_dev = js_escape(device_name)
        safe_iface = js_escape(interface_name)
        js = f'deleteLink("{safe_dev}", "{safe_iface}")'
        result = bridge_send_and_wait(js, timeout=8.0)
        if result is None:
            return "No response from PT."
        try:
            data = json.loads(result)
            if data.get("success"):
                return f"Link on {device_name}/{interface_name} deleted."
            return (
                f"Error: {data.get('error', 'unknown')}\n"
                "Note: if the method doesn't exist in this PT version, "
                "try pt_delete_device and recreate links."
            )
        except Exception:
            return f"Unexpected response: {result}"

    @mcp.tool()
    def pt_send_raw(js_code: str, wait_result: bool = False) -> str:
        """
        Send arbitrary JavaScript code to Packet Tracer via bridge.

        If wait_result=True, waits for the code to call reportResult(...).

        Parameters:
        - js_code: JavaScript code to execute in PT Script Engine
        - wait_result: if True, waits for response via reportResult()
        """
        err = check_bridge()
        if err:
            return err

        if wait_result:
            result = bridge_send_and_wait(js_code, timeout=10.0)
            if result is None:
                return "No response (timeout). Make sure the code calls reportResult(...)."
            return result

        bridge_url = get_bridge_url()
        status, _ = http_post(f"{bridge_url}/queue", js_code)
        if status == 200:
            record_command(js_code)
            return "Command sent to PT."
        return "Error sending command to bridge."
