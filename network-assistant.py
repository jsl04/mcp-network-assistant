from typing import Any
from mcp.server.fastmcp import FastMCP

# --------------------------------------------------
# Initialize the FastMCP server with a unique name.
# This name identifies the assistant when used with an MCP client like Claude Desktop.
# --------------------------------------------------
mcp = FastMCP("network-assistant")

# --------------------------------------------------
# Sample static network data.
# I am using this to focus on MCP concepts vs getting Data from a network API endpoint
# This could later be loaded from APIs (e.g., Cisco Catalyst Center, Meraki, RESTCONF, NETCONF).
# --------------------------------------------------
NETWORK_STANDARDS = {
    "routing_protocols": ["OSPF", "BGP"],
    "encapsulation": "VXLAN",
    "security_policies": {
        "ssh_required": True,
        "telnet_disabled": True
    },
    "site_layout": "hub-and-spoke",
    "approved_device_vendors": ["Cisco"]
}

DEVICE_STATUSES = {
    "core-sw1": {"cpu_usage": "32%", "status": "up"},
    "core-sw2": {"cpu_usage": "45%", "status": "up"},
    "edge-fw1": {"cpu_usage": "71%", "status": "warning"},
    "edge-fw2": {"cpu_usage": "28%", "status": "up"}
}

# --------------------------------------------------
# MCP Tool 1: Return current network standards.
# This tool is exposed to Claude via the MCP protocol.
# When the assistant needs standards context, it will call this.
# --------------------------------------------------
@mcp.tool()
async def get_network_standards() -> dict[str, Any]:
    """Returns standard routing protocols, encapsulation, and security policies."""
    return NETWORK_STANDARDS

# --------------------------------------------------
# MCP Tool 2: Return current status for a specific network device.
# The tool receives a device name and returns structured health info.
# --------------------------------------------------
@mcp.tool()
async def get_device_status(device_name: str) -> dict[str, str] | str:
    """Returns current status for a specific device.
    Args:
        device_name: e.g., 'core-sw1', 'edge-fw1'
    """
    device = DEVICE_STATUSES.get(device_name)
    if device:
        return device
    return f"No status found for device: {device_name}"


# --------------------------------------------------
# Start the MCP server using stdio transport.
# This is the method used by Claude Desktop to communicate with the assistant.
# --------------------------------------------------
if __name__ == "__main__":
    mcp.run(transport="stdio")
