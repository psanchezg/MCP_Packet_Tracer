"""Global server configuration."""

VERSION = "0.5.0"

SERVER_NAME = "Packet Tracer MCP"

SERVER_INSTRUCTIONS = (
    "MCP server for creating, configuring, and validating network topologies "
    "in Cisco Packet Tracer. Recommended tool usage order:\n"
    "1) pt_list_devices — discover available devices and ports\n"
    "2) pt_plan_topology — generate a complete plan from a request\n"
    "3) pt_validate_plan — verify the plan is correct\n"
    "4) pt_generate_script — generate the PTBuilder script\n"
    "5) pt_generate_configs — generate CLI configs\n"
    "6) pt_full_build — do everything at once (including deploy)\n"
    "7) pt_deploy — copy script to clipboard + instructions\n"
    "8) pt_live_deploy — send commands directly to PT in real time\n"
    "9) pt_bridge_status — check PT connection\n"
    "10) pt_export — export to files"
)
