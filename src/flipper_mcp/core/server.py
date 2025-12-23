"""Main Flipper MCP server implementation."""

import asyncio
from typing import Any, Sequence

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .registry import ModuleRegistry
from .flipper_client import FlipperClient
from .transport import get_transport


class FlipperMCPServer:
    """
    Main MCP server for Flipper Zero.
    
    This is the core server that:
    - Handles MCP protocol communication
    - Manages module registry
    - Delegates all tool calls to modules
    - Maintains connection to Flipper Zero
    
    The server follows a modular architecture where all functionality
    is provided by modules, not hardcoded in the server itself.
    """
    
    def __init__(self, config: dict):
        """
        Initialize Flipper MCP server.
        
        Args:
            config: Server configuration dict
        """
        self.config = config
        self.app = Server("flipper-zero-mcp")
        self.flipper: FlipperClient | None = None
        self.registry: ModuleRegistry | None = None
        self.stub_mode = False  # Whether running in stub mode (no real hardware)
        
        # Register MCP handlers
        self._register_handlers()
    
    def _register_handlers(self) -> None:
        """Register MCP protocol handlers."""
        
        @self.app.list_tools()
        async def list_tools() -> list[Tool]:
            """Return all tools from all modules."""
            if not self.registry:
                return []
            return self.registry.get_all_tools()
        
        @self.app.call_tool()
        async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
            """Route tool calls to appropriate module."""
            if not self.flipper or not self.flipper.connected:
                return [TextContent(
                    type="text",
                    text="❌ Flipper Zero not connected. Please ensure the device is connected."
                )]
            
            try:
                return await self.registry.route_tool_call(name, arguments)
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"❌ Error executing tool: {str(e)}"
                )]
    
    async def initialize(self) -> None:
        """
        Initialize server and load modules.
        
        This:
        1. Creates transport layer
        2. Connects to Flipper Zero
        3. Discovers and loads modules
        """
        print("=" * 60)
        print("Flipper Zero MCP Server - Modular Architecture")
        print("=" * 60)
        
        # Create transport based on config
        transport_type = self.config.get("transport", {}).get("type", "usb")
        
        try:
            transport = get_transport(transport_type, self.config)
        except ValueError as e:
            print(f"\n❌ {e}")
            raise
        
        # Create Flipper client
        print(f"\n🔌 Initializing {transport_type.upper()} transport...")
        self.flipper = FlipperClient(transport)
        
        # Try to connect
        print(f"   Connecting to Flipper Zero...")
        if not await self.flipper.connect():
            print("❌ Failed to connect to Flipper Zero")
            print("\n⚠️  NOTE: This is a stub implementation.")
            print("   In production, ensure Flipper Zero is connected via USB/WiFi/BLE")
            print("   Running in STUB MODE for demonstration purposes.")
            # Enable stub mode instead of forcing connection
            self.flipper.connected = True  # Stub mode
            self.stub_mode = True
        else:
            self.stub_mode = False
        
        print("✓ Connected to Flipper Zero" + (" (STUB MODE)" if self.stub_mode else ""))
        
        # Get device info
        try:
            device_info = await self.flipper.get_device_info()
            print(f"   Device: {device_info.get('name', 'Unknown')}")
            print(f"   Firmware: {device_info.get('firmware', 'Unknown')}")
        except Exception as e:
            print(f"   (Could not get device info: {e})")
        
        # Initialize module registry
        print("\n📦 Discovering modules...")
        self.registry = ModuleRegistry(self.flipper)
        self.registry.discover_modules()
        
        # Load all modules
        print("\n⚡ Loading modules...")
        await self.registry.load_all()
        
        # Print summary
        enabled_modules = [m for m in self.registry.modules.values() if m.enabled]
        total_tools = sum(len(m.get_tools()) for m in enabled_modules)
        
        print(f"\n✓ {len(enabled_modules)} module(s) loaded, {total_tools} tool(s) available")
        
        if enabled_modules:
            print("\n📋 Available modules:")
            for module in enabled_modules:
                tools = module.get_tools()
                print(f"   • {module.name} v{module.version} - {len(tools)} tool(s)")
                print(f"     {module.description}")
        else:
            print("\n⚠️  No modules loaded. The server will have no tools available.")
        
        print("\n" + "=" * 60)
        print("🚀 Server ready! Waiting for MCP connections...")
        print("=" * 60 + "\n")
    
    async def run(self) -> None:
        """
        Run the MCP server.
        
        This starts the MCP server and handles stdio communication.
        The server will run until interrupted.
        """
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.app.run(
                    read_stream,
                    write_stream,
                    self.app.create_initialization_options()
                )
        finally:
            # Cleanup
            if self.registry:
                await self.registry.unload_all()
            if self.flipper:
                await self.flipper.disconnect()
                print("\n👋 Disconnected from Flipper Zero")


async def main() -> None:
    """
    Entry point for Flipper MCP server.
    
    Loads configuration and starts the server.
    """
    # Default configuration
    # In production, this would be loaded from a config file
    config = {
        "transport": {
            "type": "usb",  # or "wifi", "bluetooth"
            "usb": {
                "port": "/dev/ttyACM0",  # Auto-detect if not specified
                "baudrate": 115200
            },
            "wifi": {
                "host": "192.168.1.1",
                "port": 8080
            },
            "bluetooth": {
                "address": None  # Auto-discover
            }
        },
        "modules": {
            # Module-specific configuration can go here
        }
    }
    
    server = FlipperMCPServer(config)
    await server.initialize()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
