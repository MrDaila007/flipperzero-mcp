# GitHub Copilot Agent Prompt: Flipper Zero MCP - Modular Architecture

## Project Vision

Create a **modular, extensible Model Context Protocol (MCP) server** for Flipper Zero that enables AI assistants to control hardware hacking tools through natural language. The architecture follows Flipper Zero's community philosophy: **core functionality + pluggable modules**, allowing developers to extend capabilities without modifying core code.

**Inspired by**: Flipper's FAP (Flipper Application Package) system, where community developers create apps that extend the device's capabilities.

## Architecture Philosophy

```
┌─────────────────────────────────────────────────────────────┐
│                    Flipper Zero MCP Server                   │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                    CORE LAYER                          │ │
│  │  • MCP Protocol Handler                               │ │
│  │  • Transport Abstraction (USB/WiFi/BLE)               │ │
│  │  • Module Registry & Loader                           │ │
│  │  • Connection Management                              │ │
│  │  • Tool Registration API                              │ │
│  └────────────────────────────────────────────────────────┘ │
│                            ▲                                 │
│                            │ Module API                      │
│       ┌────────────────────┼────────────────────┐           │
│       │                    │                    │           │
│  ┌────▼─────┐  ┌──────────▼───┐  ┌────────────▼────┐      │
│  │  BadUSB  │  │   Sub-GHz    │  │      NFC        │      │
│  │  Module  │  │   Module     │  │    Module       │      │
│  │ (Phase1) │  │  (Phase 2)   │  │   (Phase 2)     │      │
│  └──────────┘  └──────────────┘  └─────────────────┘      │
│                                                              │
│  ┌──────────┐  ┌──────────────┐  ┌─────────────────┐      │
│  │   RFID   │  │   Infrared   │  │   GPIO/I2C      │      │
│  │  Module  │  │    Module    │  │    Module       │      │
│  │(Phase 3) │  │  (Phase 3)   │  │   (Phase 3)     │      │
│  └──────────┘  └──────────────┘  └─────────────────┘      │
│                                                              │
│         ┌──────────────────────────────────┐               │
│         │  Community Modules (3rd Party)    │               │
│         │  • Custom workflows               │               │
│         │  • Vendor-specific tools          │               │
│         │  • Integration modules            │               │
│         └──────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

**Key Principle**: Each module is **self-contained**, registers its own tools, and can be developed independently. The core never needs to know about specific module implementations.

## Project Structure

```
flipper-zero-mcp/
├── README.md
├── CONTRIBUTING.md              # Module development guide
├── LICENSE
├── pyproject.toml
├── requirements.txt
│
├── src/
│   └── flipper_mcp/
│       ├── __init__.py
│       │
│       ├── core/                # CORE LAYER - Don't modify unless necessary
│       │   ├── __init__.py
│       │   ├── server.py        # MCP server implementation
│       │   ├── registry.py      # Module registry and loader
│       │   ├── transport/       # Transport abstraction
│       │   │   ├── __init__.py
│       │   │   ├── base.py      # Abstract transport interface
│       │   │   ├── usb.py       # USB serial transport
│       │   │   ├── wifi.py      # WiFi transport (ESP32)
│       │   │   └── bluetooth.py # BLE transport
│       │   ├── flipper_client.py # RPC client wrapper
│       │   └── utils.py         # Shared utilities
│       │
│       ├── modules/             # MODULES - Add new capabilities here!
│       │   ├── __init__.py
│       │   │
│       │   ├── base_module.py   # Abstract module interface
│       │   │
│       │   ├── badusb/          # 🎯 Phase 1 - Example module
│       │   │   ├── __init__.py
│       │   │   ├── module.py    # BadUSB module implementation
│       │   │   ├── generator.py # DuckyScript generator
│       │   │   ├── validator.py # Script safety validator
│       │   │   └── templates/   # Script templates
│       │   │       ├── windows.py
│       │   │       ├── macos.py
│       │   │       └── linux.py
│       │   │
│       │   ├── subghz/          # Phase 2 module
│       │   │   ├── __init__.py
│       │   │   ├── module.py
│       │   │   ├── protocols.py # Protocol decoders
│       │   │   └── analyzer.py  # Signal analysis
│       │   │
│       │   ├── nfc/             # Phase 2 module
│       │   │   ├── __init__.py
│       │   │   ├── module.py
│       │   │   ├── card_types.py
│       │   │   └── emulator.py
│       │   │
│       │   ├── rfid/            # Phase 3 module
│       │   │   └── ...
│       │   │
│       │   └── infrared/        # Phase 3 module
│       │       └── ...
│       │
│       └── cli/                 # CLI tools
│           ├── __init__.py
│           └── main.py          # Command-line interface
│
├── examples/                    # Example modules for developers
│   ├── minimal_module/         # Simplest possible module
│   ├── advanced_module/        # Full-featured example
│   └── community_template/     # Template for 3rd party modules
│
├── docs/
│   ├── architecture.md         # System architecture
│   ├── module_development.md   # How to create modules
│   ├── api_reference.md        # Core API documentation
│   ├── transport_guide.md      # Working with transports
│   └── examples/               # Example workflows
│
└── tests/
    ├── core/                   # Core tests
    ├── modules/                # Module-specific tests
    │   ├── test_badusb.py
    │   └── ...
    └── integration/            # End-to-end tests
```

## Module System Design

### The Module Interface

Every module implements a simple interface:

```python
# src/flipper_mcp/modules/base_module.py

from abc import ABC, abstractmethod
from typing import List, Any, Sequence
from mcp.types import Tool, TextContent

class FlipperModule(ABC):
    """
    Base class for all Flipper Zero MCP modules.
    
    Modules are self-contained units that:
    1. Register tools with the MCP server
    2. Handle tool execution
    3. Manage their own state
    4. Can depend on core transport layer
    """
    
    def __init__(self, flipper_client):
        """
        Initialize module with Flipper client.
        
        Args:
            flipper_client: Core Flipper RPC client (transport-agnostic)
        """
        self.flipper = flipper_client
        self.enabled = True
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Module name (e.g., 'badusb', 'subghz')"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Module version (semver)"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Short description of module capabilities"""
        pass
    
    @abstractmethod
    def get_tools(self) -> List[Tool]:
        """
        Return list of MCP tools this module provides.
        
        Tools are registered with the MCP server and become
        callable by AI assistants.
        
        Returns:
            List of Tool objects with name, description, and schema
        """
        pass
    
    @abstractmethod
    async def handle_tool_call(self, tool_name: str, arguments: Any) -> Sequence[TextContent]:
        """
        Handle execution of a tool from this module.
        
        Args:
            tool_name: Name of the tool being called
            arguments: Tool arguments from AI assistant
            
        Returns:
            List of TextContent responses
        """
        pass
    
    async def on_load(self):
        """
        Called when module is loaded.
        Use for initialization, validation, etc.
        """
        pass
    
    async def on_unload(self):
        """
        Called when module is unloaded.
        Use for cleanup.
        """
        pass
    
    def get_dependencies(self) -> List[str]:
        """
        Return list of module names this module depends on.
        
        Returns:
            List of module names (e.g., ['storage', 'system'])
        """
        return []
    
    def validate_environment(self) -> tuple[bool, str]:
        """
        Check if environment is suitable for this module.
        
        Returns:
            (is_valid, error_message)
        """
        return True, ""
```

### The Module Registry

The core maintains a registry of all modules:

```python
# src/flipper_mcp/core/registry.py

from typing import Dict, List, Optional, Type
from importlib import import_module
import inspect

class ModuleRegistry:
    """
    Central registry for all Flipper MCP modules.
    Handles loading, initialization, and lifecycle.
    """
    
    def __init__(self, flipper_client):
        self.flipper = flipper_client
        self.modules: Dict[str, FlipperModule] = {}
        self.load_order: List[str] = []
    
    def discover_modules(self, search_paths: List[str] = None):
        """
        Auto-discover modules in specified paths.
        By default, searches src/flipper_mcp/modules/
        """
        if search_paths is None:
            search_paths = ['flipper_mcp.modules']
        
        for path in search_paths:
            try:
                package = import_module(path)
                # Look for module.py files
                for item in dir(package):
                    if item.startswith('_'):
                        continue
                    
                    submodule = import_module(f"{path}.{item}")
                    
                    # Find classes that inherit from FlipperModule
                    for name, obj in inspect.getmembers(submodule):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, FlipperModule) and 
                            obj is not FlipperModule):
                            
                            # Found a module!
                            self.register_module(obj)
                            
            except ImportError as e:
                print(f"Warning: Could not import {path}: {e}")
    
    def register_module(self, module_class: Type[FlipperModule]):
        """Register a module class"""
        # Instantiate the module
        module = module_class(self.flipper)
        
        # Validate environment
        is_valid, error = module.validate_environment()
        if not is_valid:
            print(f"Module {module.name} not loaded: {error}")
            return
        
        # Check dependencies
        missing_deps = [
            dep for dep in module.get_dependencies() 
            if dep not in self.modules
        ]
        
        if missing_deps:
            print(f"Module {module.name} missing dependencies: {missing_deps}")
            return
        
        self.modules[module.name] = module
        self.load_order.append(module.name)
        print(f"✓ Registered module: {module.name} v{module.version}")
    
    async def load_all(self):
        """Load all registered modules"""
        for name in self.load_order:
            module = self.modules[name]
            try:
                await module.on_load()
                print(f"✓ Loaded: {name}")
            except Exception as e:
                print(f"✗ Failed to load {name}: {e}")
                module.enabled = False
    
    def get_all_tools(self) -> List[Tool]:
        """Collect tools from all enabled modules"""
        tools = []
        for module in self.modules.values():
            if module.enabled:
                tools.extend(module.get_tools())
        return tools
    
    async def route_tool_call(self, tool_name: str, arguments: Any) -> Sequence[TextContent]:
        """Route tool call to appropriate module"""
        # Find which module owns this tool
        for module in self.modules.values():
            if not module.enabled:
                continue
            
            tool_names = [tool.name for tool in module.get_tools()]
            if tool_name in tool_names:
                return await module.handle_tool_call(tool_name, arguments)
        
        # Tool not found
        return [TextContent(
            type="text",
            text=f"Error: Tool '{tool_name}' not found in any module"
        )]
```

## Phase 1: BadUSB Module (Reference Implementation)

This serves as the **example** for how to build modules:

```python
# src/flipper_mcp/modules/badusb/module.py

from typing import List, Any, Sequence
from mcp.types import Tool, TextContent

from ..base_module import FlipperModule
from .generator import DuckyScriptGenerator
from .validator import ScriptValidator

class BadUSBModule(FlipperModule):
    """
    BadUSB module for keyboard/mouse emulation.
    
    Provides natural language → DuckyScript generation and execution.
    This is the Phase 1 reference implementation showing how modules work.
    """
    
    @property
    def name(self) -> str:
        return "badusb"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "BadUSB keyboard/mouse emulation with AI-powered script generation"
    
    def __init__(self, flipper_client):
        super().__init__(flipper_client)
        self.generator = DuckyScriptGenerator()
        self.validator = ScriptValidator()
        self.badusb_path = "/ext/badusb"
    
    def get_tools(self) -> List[Tool]:
        """Register BadUSB tools with MCP server"""
        return [
            Tool(
                name="badusb_list",
                description="List all BadUSB scripts stored on Flipper Zero",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="badusb_read",
                description="Read contents of a BadUSB script",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "Script filename (e.g., 'test.txt')"
                        }
                    },
                    "required": ["filename"]
                }
            ),
            Tool(
                name="badusb_generate",
                description="Generate BadUSB DuckyScript from natural language description",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "What the script should do"
                        },
                        "target_os": {
                            "type": "string",
                            "enum": ["windows", "macos", "linux"],
                            "default": "windows"
                        },
                        "filename": {
                            "type": "string",
                            "description": "Script filename",
                            "default": "ai_generated.txt"
                        }
                    },
                    "required": ["description"]
                }
            ),
            Tool(
                name="badusb_execute",
                description="Execute a BadUSB script on the target device",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "Script to execute"
                        },
                        "confirm": {
                            "type": "boolean",
                            "description": "Must be true (safety confirmation)",
                            "default": False
                        }
                    },
                    "required": ["filename", "confirm"]
                }
            ),
            Tool(
                name="badusb_workflow",
                description="Complete workflow: generate, validate, save, and optionally execute",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "What to do"
                        },
                        "target_os": {
                            "type": "string",
                            "enum": ["windows", "macos", "linux"],
                            "default": "windows"
                        },
                        "execute": {
                            "type": "boolean",
                            "description": "Execute after generation",
                            "default": False
                        }
                    },
                    "required": ["description"]
                }
            ),
        ]
    
    async def handle_tool_call(self, tool_name: str, arguments: Any) -> Sequence[TextContent]:
        """Handle tool execution for BadUSB module"""
        
        if tool_name == "badusb_list":
            return await self._list_scripts()
        
        elif tool_name == "badusb_read":
            return await self._read_script(arguments["filename"])
        
        elif tool_name == "badusb_generate":
            return await self._generate_script(
                arguments["description"],
                arguments.get("target_os", "windows"),
                arguments.get("filename", "ai_generated.txt")
            )
        
        elif tool_name == "badusb_execute":
            return await self._execute_script(
                arguments["filename"],
                arguments.get("confirm", False)
            )
        
        elif tool_name == "badusb_workflow":
            return await self._workflow(
                arguments["description"],
                arguments.get("target_os", "windows"),
                arguments.get("execute", False)
            )
        
        return [TextContent(
            type="text",
            text=f"Error: Unknown BadUSB tool '{tool_name}'"
        )]
    
    async def _list_scripts(self) -> Sequence[TextContent]:
        """List all BadUSB scripts"""
        files = await self.flipper.storage.list(self.badusb_path)
        
        if not files:
            return [TextContent(
                type="text",
                text=f"No BadUSB scripts found in {self.badusb_path}"
            )]
        
        result = f"BadUSB Scripts ({len(files)}):\n\n"
        for f in files:
            result += f"• {f}\n"
        
        return [TextContent(type="text", text=result)]
    
    async def _read_script(self, filename: str) -> Sequence[TextContent]:
        """Read script contents"""
        path = f"{self.badusb_path}/{filename}"
        content = await self.flipper.storage.read(path)
        
        return [TextContent(
            type="text",
            text=f"Contents of {filename}:\n\n```duckyscript\n{content}\n```"
        )]
    
    async def _generate_script(
        self, description: str, target_os: str, filename: str
    ) -> Sequence[TextContent]:
        """Generate and save BadUSB script"""
        
        # Generate script
        script = self.generator.generate(description, target_os)
        
        # Validate for safety
        is_valid, error = self.validator.validate(script)
        if not is_valid:
            return [TextContent(
                type="text",
                text=f"❌ Script validation failed: {error}\n\n{script}"
            )]
        
        # Save to Flipper
        path = f"{self.badusb_path}/{filename}"
        await self.flipper.storage.write(path, script)
        
        result = f"✓ BadUSB script generated: {filename}\n\n"
        result += f"Description: {description}\n"
        result += f"Target OS: {target_os}\n\n"
        result += f"Script:\n```duckyscript\n{script}\n```"
        
        return [TextContent(type="text", text=result)]
    
    async def _execute_script(self, filename: str, confirm: bool) -> Sequence[TextContent]:
        """Execute BadUSB script"""
        
        if not confirm:
            return [TextContent(
                type="text",
                text="❌ Execution blocked: 'confirm' must be true"
            )]
        
        path = f"{self.badusb_path}/{filename}"
        
        # Read script first (for display)
        content = await self.flipper.storage.read(path)
        
        # Execute
        success = await self.flipper.app.launch("BadUsb", path)
        
        result = f"⚠️ Executing: {filename}\n\n"
        result += f"Script:\n```duckyscript\n{content}\n```\n\n"
        
        if success:
            result += "✓ Script execution initiated"
        else:
            result += "❌ Execution failed"
        
        return [TextContent(type="text", text=result)]
    
    async def _workflow(
        self, description: str, target_os: str, execute: bool
    ) -> Sequence[TextContent]:
        """Complete workflow"""
        
        result = "🤖 BadUSB Workflow\n\n"
        
        # Generate
        result += "Step 1: Generating script...\n"
        script = self.generator.generate(description, target_os)
        
        # Validate
        result += "Step 2: Validating...\n"
        is_valid, error = self.validator.validate(script)
        
        if not is_valid:
            result += f"❌ Validation failed: {error}"
            return [TextContent(type="text", text=result)]
        
        result += "✓ Valid\n\n"
        
        # Save
        result += "Step 3: Saving...\n"
        filename = "ai_workflow.txt"
        path = f"{self.badusb_path}/{filename}"
        await self.flipper.storage.write(path, script)
        result += f"✓ Saved as {filename}\n\n"
        
        # Execute (optional)
        if execute:
            result += "Step 4: Executing...\n"
            success = await self.flipper.app.launch("BadUsb", path)
            result += "✓ Execution started\n\n" if success else "❌ Failed\n\n"
        else:
            result += "Step 4: Skipped (execute=false)\n\n"
        
        result += f"Generated Script:\n```duckyscript\n{script}\n```"
        
        return [TextContent(type="text", text=result)]
    
    def validate_environment(self) -> tuple[bool, str]:
        """Check if BadUSB is available"""
        # Could check firmware version, BadUSB app presence, etc.
        return True, ""
    
    def get_dependencies(self) -> List[str]:
        """BadUSB depends on storage module"""
        return ["storage"]
```

## Core Server Implementation

The core server is now much simpler - it just manages modules:

```python
# src/flipper_mcp/core/server.py

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
    
    This is the core - it handles MCP protocol and delegates
    all tool calls to modules.
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.app = Server("flipper-zero-mcp")
        self.flipper: FlipperClient = None
        self.registry: ModuleRegistry = None
        
        # Register MCP handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register MCP protocol handlers"""
        
        @self.app.list_tools()
        async def list_tools() -> list[Tool]:
            """Return all tools from all modules"""
            if not self.registry:
                return []
            return self.registry.get_all_tools()
        
        @self.app.call_tool()
        async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
            """Route tool calls to appropriate module"""
            if not self.flipper or not self.flipper.connected:
                return [TextContent(
                    type="text",
                    text="❌ Flipper Zero not connected"
                )]
            
            try:
                return await self.registry.route_tool_call(name, arguments)
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=f"❌ Error: {str(e)}"
                )]
    
    async def initialize(self):
        """Initialize server and load modules"""
        
        print("=" * 60)
        print("Flipper Zero MCP Server - Modular Architecture")
        print("=" * 60)
        
        # Create transport based on config
        transport_type = self.config.get("transport", {}).get("type", "usb")
        transport = get_transport(transport_type, self.config)
        
        # Create Flipper client
        print(f"\nInitializing {transport_type} transport...")
        self.flipper = FlipperClient(transport)
        
        if not await self.flipper.connect():
            raise Exception("Failed to connect to Flipper Zero")
        
        print("✓ Connected to Flipper Zero")
        
        # Initialize module registry
        print("\nDiscovering modules...")
        self.registry = ModuleRegistry(self.flipper)
        self.registry.discover_modules()
        
        # Load all modules
        print("\nLoading modules...")
        await self.registry.load_all()
        
        # Print summary
        enabled_modules = [m for m in self.registry.modules.values() if m.enabled]
        print(f"\n✓ {len(enabled_modules)} modules loaded")
        print("\nAvailable modules:")
        for module in enabled_modules:
            tools = module.get_tools()
            print(f"  • {module.name} v{module.version} ({len(tools)} tools)")
        
        print("\n" + "=" * 60)
        print("Server ready! Waiting for MCP connections...")
        print("=" * 60 + "\n")
    
    async def run(self):
        """Run the MCP server"""
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.app.run(
                    read_stream,
                    write_stream,
                    self.app.create_initialization_options()
                )
        finally:
            if self.flipper:
                await self.flipper.disconnect()

async def main():
    """Entry point"""
    # Load config (simplified for example)
    config = {
        "transport": {
            "type": "usb",  # or "wifi", "bluetooth"
            "usb": {
                "port": "/dev/ttyACM0",
                "baudrate": 115200
            }
        }
    }
    
    server = FlipperMCPServer(config)
    await server.initialize()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
```

## Creating Your Own Module

### Step 1: Create Module Structure

```bash
mkdir -p src/flipper_mcp/modules/mymodule
cd src/flipper_mcp/modules/mymodule
touch __init__.py module.py
```

### Step 2: Implement Module Class

```python
# src/flipper_mcp/modules/mymodule/module.py

from typing import List, Any, Sequence
from mcp.types import Tool, TextContent
from ..base_module import FlipperModule

class MyModule(FlipperModule):
    """
    My custom Flipper Zero module.
    
    TODO: Describe what your module does
    """
    
    @property
    def name(self) -> str:
        return "mymodule"
    
    @property
    def version(self) -> str:
        return "0.1.0"
    
    @property
    def description(self) -> str:
        return "My custom module description"
    
    def get_tools(self) -> List[Tool]:
        """Define your tools"""
        return [
            Tool(
                name="mymodule_action",
                description="Does something cool with Flipper Zero",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "param": {
                            "type": "string",
                            "description": "A parameter"
                        }
                    },
                    "required": ["param"]
                }
            ),
        ]
    
    async def handle_tool_call(
        self, tool_name: str, arguments: Any
    ) -> Sequence[TextContent]:
        """Handle tool execution"""
        
        if tool_name == "mymodule_action":
            param = arguments["param"]
            
            # Do something with Flipper
            result = await self.flipper.some_operation(param)
            
            return [TextContent(
                type="text",
                text=f"✓ Action completed: {result}"
            )]
        
        return [TextContent(
            type="text",
            text=f"Unknown tool: {tool_name}"
        )]
    
    async def on_load(self):
        """Initialize module"""
        print(f"MyModule loaded!")
    
    def validate_environment(self) -> tuple[bool, str]:
        """Check if environment is suitable"""
        # Check firmware version, required apps, etc.
        return True, ""
```

### Step 3: Export Module

```python
# src/flipper_mcp/modules/mymodule/__init__.py

from .module import MyModule

__all__ = ['MyModule']
```

### Step 4: Test It

```bash
python -m flipper_mcp.core.server
```

Your module is automatically discovered and loaded! 🎉

## Module Development Guidelines

### Module Best Practices

1. **Self-contained**: Don't modify core code
2. **Clear naming**: Use descriptive tool names (e.g., `badusb_generate`, not `generate`)
3. **Error handling**: Always handle exceptions gracefully
4. **Validation**: Validate all inputs before Flipper operations
5. **Safety**: Implement safety checks for dangerous operations
6. **Documentation**: Include docstrings and examples
7. **Testing**: Write tests for your module
8. **Dependencies**: Clearly declare module dependencies

### Tool Naming Convention

**Format**: `{module}_{action}`

**Examples**:
- `badusb_generate` (BadUSB module, generate action)
- `subghz_scan` (Sub-GHz module, scan action)
- `nfc_read` (NFC module, read action)

**Why?** Makes it obvious which module owns which tool. Prevents name collisions.

### Module Configuration

If your module needs configuration:

```python
class MyModule(FlipperModule):
    def __init__(self, flipper_client, config: dict = None):
        super().__init__(flipper_client)
        self.config = config or {}
        
        # Load module-specific config
        self.my_setting = self.config.get("my_setting", "default")
```

Pass config during registration:

```python
# In core/server.py
module = MyModule(flipper, config=module_config)
```

### Module Testing

```python
# tests/modules/test_mymodule.py

import pytest
from unittest.mock import Mock, AsyncMock
from flipper_mcp.modules.mymodule import MyModule

@pytest.fixture
def mock_flipper():
    client = Mock()
    client.some_operation = AsyncMock(return_value="success")
    return client

@pytest.mark.asyncio
async def test_mymodule_action(mock_flipper):
    module = MyModule(mock_flipper)
    
    result = await module.handle_tool_call(
        "mymodule_action",
        {"param": "test"}
    )
    
    assert len(result) == 1
    assert "completed" in result[0].text
```

## Example Modules to Build

### Module: Sub-GHz Radio

```python
class SubGHzModule(FlipperModule):
    """
    Sub-GHz radio operations.
    
    Tools:
    - subghz_scan: Scan for signals on a frequency
    - subghz_read: Read and decode signal
    - subghz_transmit: Transmit a saved signal
    - subghz_analyze: Analyze signal properties
    """
    
    @property
    def name(self) -> str:
        return "subghz"
```

### Module: NFC/RFID

```python
class NFCModule(FlipperModule):
    """
    NFC card operations.
    
    Tools:
    - nfc_scan: Detect nearby NFC cards
    - nfc_read: Read card data
    - nfc_emulate: Emulate a card
    - nfc_write: Write to magic cards
    """
    
    @property
    def name(self) -> str:
        return "nfc"
```

### Module: Infrared

```python
class InfraredModule(FlipperModule):
    """
    IR remote control.
    
    Tools:
    - ir_learn: Learn IR signal from remote
    - ir_send: Send IR command
    - ir_universal: Use universal remote database
    """
    
    @property
    def name(self) -> str:
        return "infrared"
```

### Module: GPIO/I2C

```python
class GPIOModule(FlipperModule):
    """
    GPIO pin control and I2C communication.
    
    Tools:
    - gpio_read: Read pin state
    - gpio_write: Set pin state
    - i2c_scan: Scan for I2C devices
    - i2c_read: Read from I2C device
    """
    
    @property
    def name(self) -> str:
        return "gpio"
```

### Module: Automation/Workflows

```python
class WorkflowModule(FlipperModule):
    """
    Multi-stage automation workflows.
    
    Combines multiple modules for complex attacks.
    
    Tools:
    - workflow_create: Define a workflow
    - workflow_execute: Run a workflow
    - workflow_save: Save workflow for reuse
    """
    
    @property
    def name(self) -> str:
        return "workflow"
    
    def get_dependencies(self) -> List[str]:
        return ["badusb", "subghz", "nfc"]  # Requires multiple modules
```

## Community Module Development

### Publishing Your Module

**Option 1: Standalone Package**

```bash
# Create separate repo
flipper-mcp-mymodule/
├── pyproject.toml
├── src/
│   └── flipper_mcp_mymodule/
│       ├── __init__.py
│       └── module.py
└── README.md

# Users install with:
pip install flipper-mcp-mymodule

# Auto-discovered if follows naming convention
```

**Option 2: Submit to Main Repo**

1. Fork the main repository
2. Create your module in `src/flipper_mcp/modules/`
3. Add tests
4. Submit pull request
5. Maintainers review and merge

**Option 3: Module Registry (Future)**

```bash
# Install from community registry
flipper-mcp install community/awesome-module

# Browse available modules
flipper-mcp browse
```

### Module Template Repository

We provide a template repository:

```
https://github.com/yourorg/flipper-mcp-module-template
```

**Features**:
- Pre-configured project structure
- GitHub Actions CI/CD
- Testing setup
- Documentation template
- Example implementation

**Usage**:
```bash
# Use template
gh repo create my-flipper-module --template flipper-mcp-module-template

# Implement your module
cd my-flipper-module
# Edit src/module.py

# Test it
pytest

# Publish
poetry build
poetry publish
```

## Advanced: Module Communication

Modules can communicate with each other:

```python
class AdvancedModule(FlipperModule):
    """Module that uses other modules"""
    
    def __init__(self, flipper_client, registry):
        super().__init__(flipper_client)
        self.registry = registry
    
    async def handle_tool_call(self, tool_name, arguments):
        # Get another module
        badusb = self.registry.modules.get("badusb")
        
        if badusb:
            # Use its functionality
            result = await badusb.handle_tool_call(
                "badusb_generate",
                {"description": "test"}
            )
        
        return result
```

## Module Lifecycle Hooks

```python
class MyModule(FlipperModule):
    
    async def on_load(self):
        """Called when module loads"""
        # Initialize resources
        self.cache = {}
        print(f"{self.name} loaded")
    
    async def on_unload(self):
        """Called when module unloads"""
        # Cleanup resources
        self.cache.clear()
        print(f"{self.name} unloaded")
    
    async def on_connection(self):
        """Called when Flipper connects"""
        # Verify module requirements
        version = await self.flipper.get_firmware_version()
        print(f"Firmware: {version}")
    
    async def on_disconnection(self):
        """Called when Flipper disconnects"""
        # Handle disconnect gracefully
        print(f"{self.name}: Connection lost")
```

## Module Configuration Schema

```yaml
# config.yaml

modules:
  badusb:
    enabled: true
    config:
      default_os: windows
      auto_validate: true
      templates_path: ./templates
  
  subghz:
    enabled: true
    config:
      default_frequency: 433.92
      max_power: 10
  
  nfc:
    enabled: false
    config:
      reason: "Not needed for this deployment"
  
  mymodule:
    enabled: true
    config:
      custom_setting: "value"
```

## Documentation Requirements

Every module should have:

### 1. Module README

```markdown
# MyModule

Brief description of what the module does.

## Features

- Feature 1
- Feature 2

## Installation

```bash
pip install flipper-mcp-mymodule
```

## Tools

### `mymodule_action`

Description of the tool.

**Parameters**:
- `param1`: Description
- `param2`: Description

**Example**:
```
User: "Use my module to do something"
Claude: [calls mymodule_action]
```

## Configuration

Optional configuration options.

## Dependencies

- Module dependencies
- Firmware requirements
```

### 2. API Documentation

Document all public methods, especially those in the module interface.

### 3. Examples

Provide example usage scenarios.

## Testing Modules

### Unit Tests

```python
# tests/modules/test_mymodule.py

import pytest
from flipper_mcp.modules.mymodule import MyModule

def test_module_properties():
    module = MyModule(mock_flipper)
    assert module.name == "mymodule"
    assert module.version != ""

@pytest.mark.asyncio
async def test_tool_execution():
    module = MyModule(mock_flipper)
    result = await module.handle_tool_call("mymodule_action", {})
    assert result is not None
```

### Integration Tests

```python
# tests/integration/test_mymodule_integration.py

@pytest.mark.integration
async def test_with_real_flipper():
    """Test with actual Flipper Zero hardware"""
    # Requires real device
    pass
```

## Performance Considerations

### Caching

```python
from functools import lru_cache

class MyModule(FlipperModule):
    
    @lru_cache(maxsize=128)
    async def expensive_operation(self, param):
        """Cache results of expensive operations"""
        result = await self.flipper.complex_operation(param)
        return result
```

### Async Best Practices

```python
class MyModule(FlipperModule):
    
    async def handle_tool_call(self, tool_name, arguments):
        # Use asyncio.gather for parallel operations
        results = await asyncio.gather(
            self.operation_1(),
            self.operation_2(),
            self.operation_3()
        )
        return results
```

## Security Considerations

### Input Validation

```python
class MyModule(FlipperModule):
    
    def _validate_input(self, value: str) -> bool:
        """Validate user input"""
        # Check for injection attacks
        dangerous_chars = [';', '&&', '||', '`', '$']
        return not any(char in value for char in dangerous_chars)
    
    async def handle_tool_call(self, tool_name, arguments):
        param = arguments["param"]
        
        if not self._validate_input(param):
            return [TextContent(
                type="text",
                text="❌ Invalid input detected"
            )]
        
        # Proceed with operation
```

### Permission Checking

```python
class DangerousModule(FlipperModule):
    """Module that performs dangerous operations"""
    
    def __init__(self, flipper_client, permissions: set):
        super().__init__(flipper_client)
        self.permissions = permissions
    
    async def handle_tool_call(self, tool_name, arguments):
        # Check if user has permission
        if "dangerous_operation" not in self.permissions:
            return [TextContent(
                type="text",
                text="❌ Permission denied"
            )]
        
        # Proceed
```

## Debugging Modules

### Logging

```python
import logging

class MyModule(FlipperModule):
    
    def __init__(self, flipper_client):
        super().__init__(flipper_client)
        self.logger = logging.getLogger(f"flipper_mcp.{self.name}")
    
    async def handle_tool_call(self, tool_name, arguments):
        self.logger.info(f"Tool called: {tool_name}")
        self.logger.debug(f"Arguments: {arguments}")
        
        try:
            result = await self._do_something()
            self.logger.info("Operation successful")
            return result
        except Exception as e:
            self.logger.error(f"Operation failed: {e}")
            raise
```

### Debug Mode

```python
class MyModule(FlipperModule):
    
    def __init__(self, flipper_client, debug: bool = False):
        super().__init__(flipper_client)
        self.debug = debug
    
    async def handle_tool_call(self, tool_name, arguments):
        if self.debug:
            print(f"[DEBUG] {self.name}.{tool_name} called")
            print(f"[DEBUG] Arguments: {arguments}")
        
        result = await self._execute(tool_name, arguments)
        
        if self.debug:
            print(f"[DEBUG] Result: {result}")
        
        return result
```

## Phase 1 Implementation Checklist

### Core (Must Have)
- [ ] Transport abstraction (USB, WiFi, BLE)
- [ ] Flipper RPC client
- [ ] Module registry and loader
- [ ] MCP server implementation
- [ ] Configuration management
- [ ] Basic error handling

### BadUSB Module (Reference Implementation)
- [ ] Module class implementation
- [ ] Tool registration
- [ ] DuckyScript generator
- [ ] Script validator
- [ ] File operations (list, read, write)
- [ ] Script execution
- [ ] Workflow automation
- [ ] Safety checks
- [ ] Template system
- [ ] Tests

### Documentation
- [ ] Architecture overview
- [ ] Module development guide
- [ ] API reference
- [ ] Example modules
- [ ] Contributing guide
- [ ] Security guidelines

### DevEx (Developer Experience)
- [ ] Module template repository
- [ ] CLI for module management
- [ ] Automatic module discovery
- [ ] Hot-reloading modules (dev mode)
- [ ] Module testing framework

## Success Criteria

Phase 1 is complete when:

1. ✅ Core server runs and connects to Flipper
2. ✅ Module registry auto-discovers modules
3. ✅ BadUSB module fully functional (reference implementation)
4. ✅ Someone can create a new module without modifying core
5. ✅ Module can be loaded without restarting server
6. ✅ Documentation enables community contributions
7. ✅ At least 1 community module exists

## Future Enhancements

### Phase 2: More Modules
- Sub-GHz module
- NFC/RFID module
- Infrared module
- Storage management module

### Phase 3: Advanced Features
- Module marketplace/registry
- Module version management
- Hot-reloading modules
- Module permissions system
- Cross-module workflows
- Module analytics/telemetry

### Phase 4: Ecosystem
- Web UI for module management
- Module authoring tools
- Certified module program
- Community module library
- Module templates for common patterns

## Contributing

See `CONTRIBUTING.md` for:
- Code style guide
- Pull request process
- Module submission guidelines
- Testing requirements
- Documentation standards

## Resources for Module Developers

### Example Repositories
- `flipper-mcp-badusb` - Reference implementation
- `flipper-mcp-template` - Module template
- `flipper-mcp-examples` - Example modules

### Documentation
- Module API Reference
- Core API Reference
- Transport Guide
- Testing Guide
- Security Best Practices

### Community
- Discord: `#module-development` channel
- Forum: Flipper MCP category
- GitHub Discussions: Q&A and ideas

---

## Final Instructions for GitHub Copilot Agent

Implement this modular Flipper Zero MCP server with these priorities:

1. **Core first**: Get transport abstraction and module registry working
2. **BadUSB as example**: Implement as a proper module (not hardcoded in core)
3. **Clean separation**: Core should never know about specific modules
4. **Developer-friendly**: Make module creation as simple as possible
5. **Well-documented**: Every interface needs clear documentation
6. **Testable**: Write tests showing how modules work
7. **Extensible**: Design for future modules we haven't thought of yet

The goal is a system where the community can build Flipper capabilities without touching core code, just like Flipper's FAP system enables app development without firmware modifications.

Build the **platform**, not just the tools. 🐬🔧
