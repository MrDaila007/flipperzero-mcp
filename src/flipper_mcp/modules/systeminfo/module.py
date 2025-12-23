"""System Info module for Flipper Zero MCP."""

from typing import Any, List, Sequence
from mcp.types import Tool, TextContent

from ..base_module import FlipperModule


class SystemInfoModule(FlipperModule):
    """
    System Info module for Flipper Zero.
    
    Provides a simple tool to check connection status and retrieve
    system information about the connected Flipper Zero device.
    This is the simplest module in the project.
    """
    
    @property
    def name(self) -> str:
        """Module name."""
        return "systeminfo"
    
    @property
    def version(self) -> str:
        """Module version."""
        return "1.0.0"
    
    @property
    def description(self) -> str:
        """Module description."""
        return "Check Flipper Zero connection and retrieve system information"
    
    def get_tools(self) -> List[Tool]:
        """Register System Info tools with MCP server."""
        return [
            Tool(
                name="systeminfo_get",
                description="Get system information about the connected Flipper Zero device including name, firmware version, serial number, and connection details",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
        ]
    
    async def handle_tool_call(
        self, tool_name: str, arguments: Any
    ) -> Sequence[TextContent]:
        """Handle tool execution for System Info module."""
        
        if tool_name == "systeminfo_get":
            return await self._get_system_info()
        
        return [TextContent(
            type="text",
            text=f"❌ Error: Unknown System Info tool '{tool_name}'"
        )]
    
    async def _get_system_info(self) -> Sequence[TextContent]:
        """Get system information about the connected Flipper Zero."""
        try:
            result = "📱 Flipper Zero System Information\n"
            result += "=" * 50 + "\n\n"
            
            # Connection status
            is_connected = self.flipper.connected
            result += f"🔌 Connection Status: {'✅ Connected' if is_connected else '❌ Not Connected'}\n\n"
            
            if not is_connected:
                result += "⚠️  Device is not connected. Some information may be unavailable.\n\n"
            
            # Device information
            try:
                device_info = await self.flipper.get_device_info()
                result += "📟 Device Information:\n"
                result += f"   Name: {device_info.get('name', 'Unknown')}\n"
                result += f"   Hardware: {device_info.get('hardware', 'Unknown')}\n"
                result += f"   Firmware: {device_info.get('firmware', 'Unknown')}\n\n"
            except Exception as e:
                result += f"⚠️  Could not retrieve device info: {str(e)}\n\n"
            
            # Firmware version (try separate call)
            try:
                firmware_version = await self.flipper.get_firmware_version()
                if firmware_version and firmware_version != "Unknown":
                    result += f"🔧 Firmware Version: {firmware_version}\n\n"
            except Exception:
                pass  # Already included in device_info
            
            # Transport information
            if self.flipper.transport:
                transport = self.flipper.transport
                result += "🔗 Transport Information:\n"
                result += f"   Type: {transport.get_name()}\n"
                
                # Get port if available (USB transport)
                if hasattr(transport, 'port'):
                    result += f"   Port: {transport.port}\n"
                
                # Get host if available (WiFi transport)
                if hasattr(transport, 'host'):
                    result += f"   Host: {transport.host}\n"
                    if hasattr(transport, 'port'):
                        result += f"   Port: {transport.port}\n"
                
                result += "\n"
            
            # Serial number (if available via RPC)
            try:
                if self.flipper.rpc:
                    # Try to get serial number via RPC
                    # Note: This may not be available in all firmware versions
                    rpc_info = await self.flipper.rpc.get_device_info()
                    if isinstance(rpc_info, dict) and 'serial' in rpc_info:
                        result += f"🔢 Serial Number: {rpc_info['serial']}\n\n"
                    elif isinstance(rpc_info, dict) and 'serial_number' in rpc_info:
                        result += f"🔢 Serial Number: {rpc_info['serial_number']}\n\n"
            except Exception:
                pass  # Serial number may not be available
            
            # Additional system info if available
            try:
                if self.flipper.rpc:
                    rpc_info = await self.flipper.rpc.get_device_info()
                    if isinstance(rpc_info, dict):
                        # Include any additional fields
                        additional_fields = {
                            k: v for k, v in rpc_info.items()
                            if k not in ['name', 'hardware', 'firmware', 'serial', 'serial_number']
                            and v not in [None, '', 'Unknown']
                        }
                        if additional_fields:
                            result += "📊 Additional Information:\n"
                            for key, value in additional_fields.items():
                                result += f"   {key.replace('_', ' ').title()}: {value}\n"
                            result += "\n"
            except Exception:
                pass
            
            result += "=" * 50
            
            return [TextContent(type="text", text=result)]
            
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"❌ Error retrieving system information: {str(e)}"
            )]
    
    def validate_environment(self) -> tuple[bool, str]:
        """System Info module is always available."""
        return True, ""
    
    def get_dependencies(self) -> List[str]:
        """System Info has no module dependencies."""
        return []
    
    async def on_load(self) -> None:
        """Called when module is loaded."""
        pass
    
    async def on_unload(self) -> None:
        """Called when module is unloaded."""
        pass

