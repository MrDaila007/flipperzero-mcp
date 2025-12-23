# API Reference

Complete API reference for Flipper Zero MCP.

## Core API

### FlipperMCPServer

Main server class.

```python
from flipper_mcp.core.server import FlipperMCPServer

server = FlipperMCPServer(config)
await server.initialize()
await server.run()
```

**Methods:**

- `__init__(config: dict)` - Initialize server with configuration
- `async initialize()` - Initialize transports and modules
- `async run()` - Start MCP server (blocking)

### ModuleRegistry

Module discovery and management.

```python
from flipper_mcp.core.registry import ModuleRegistry

registry = ModuleRegistry(flipper_client)
registry.discover_modules()
await registry.load_all()
```

**Methods:**

- `discover_modules(search_paths: List[str] = None)` - Auto-discover modules
- `register_module(module_class: Type[FlipperModule])` - Register a module class
- `async load_all()` - Load all registered modules
- `async unload_all()` - Unload all modules
- `get_all_tools() -> List[Tool]` - Get tools from all modules
- `async route_tool_call(tool_name: str, arguments: Any)` - Route tool to module
- `get_module(name: str) -> FlipperModule | None` - Get module by name
- `list_modules() -> List[Dict]` - List all modules

### FlipperClient

High-level Flipper Zero client.

```python
from flipper_mcp.core.flipper_client import FlipperClient

client = FlipperClient(transport)
await client.connect()
```

**Methods:**

- `async connect() -> bool` - Connect to Flipper
- `async disconnect()` - Disconnect from Flipper
- `async get_firmware_version() -> str` - Get firmware version
- `async get_device_info() -> dict` - Get device information
- `async send_rpc(command: str, params: dict) -> dict` - Send RPC command

**Properties:**

- `storage: FlipperStorage` - File system operations
- `app: FlipperApp` - Application launcher

### FlipperStorage

File system operations.

```python
# Access via client
files = await client.storage.list("/ext/badusb")
```

**Methods:**

- `async list(path: str) -> List[str]` - List directory
- `async read(path: str) -> str` - Read file
- `async write(path: str, content: str) -> bool` - Write file
- `async delete(path: str) -> bool` - Delete file
- `async mkdir(path: str) -> bool` - Create directory

### FlipperApp

Application launcher.

```python
# Access via client
await client.app.launch("BadUsb", "/ext/badusb/script.txt")
```

**Methods:**

- `async launch(app_name: str, args: str = None) -> bool` - Launch app
- `async stop(app_name: str) -> bool` - Stop app

## Transport API

### FlipperTransport

Abstract transport interface.

```python
from flipper_mcp.core.transport.base import FlipperTransport

class MyTransport(FlipperTransport):
    async def connect(self) -> bool: ...
    async def send(self, data: bytes) -> None: ...
    async def receive(self, timeout: float = None) -> bytes: ...
```

**Methods:**

- `async connect() -> bool` - Establish connection
- `async disconnect()` - Close connection
- `async send(data: bytes)` - Send data
- `async receive(timeout: float = None) -> bytes` - Receive data
- `async is_connected() -> bool` - Check connection status
- `get_name() -> str` - Get transport name

### USBTransport

USB serial transport.

```python
from flipper_mcp.core.transport import USBTransport

transport = USBTransport({
    "port": "/dev/ttyACM0",
    "baudrate": 115200
})
```

**Config:**

- `port: str` - Serial port (auto-detected if not specified)
- `baudrate: int` - Baud rate (default: 115200)
- `timeout: float` - Read timeout (default: 1.0)

### WiFiTransport

WiFi (ESP32) transport.

```python
from flipper_mcp.core.transport import WiFiTransport

transport = WiFiTransport({
    "host": "192.168.1.1",
    "port": 8080
})
```

**Config:**

- `host: str` - IP address (default: 192.168.1.1)
- `port: int` - Port number (default: 8080)

### BluetoothTransport

Bluetooth LE transport (stub).

```python
from flipper_mcp.core.transport import BluetoothTransport

transport = BluetoothTransport({
    "address": "00:11:22:33:44:55"
})
```

**Config:**

- `address: str` - BLE address

### get_transport()

Transport factory function.

```python
from flipper_mcp.core.transport import get_transport

transport = get_transport("usb", config)
```

**Parameters:**

- `transport_type: str` - Transport type ("usb", "wifi", "bluetooth")
- `config: dict` - Configuration dict

**Returns:** Transport instance

## Module API

### FlipperModule

Base class for all modules.

```python
from flipper_mcp.modules.base_module import FlipperModule

class MyModule(FlipperModule):
    @property
    def name(self) -> str:
        return "mymodule"
    
    def get_tools(self) -> List[Tool]:
        return [...]
    
    async def handle_tool_call(self, tool_name: str, arguments: Any):
        ...
```

**Required Properties:**

- `name: str` - Module identifier
- `version: str` - Semantic version
- `description: str` - One-line description

**Required Methods:**

- `get_tools() -> List[Tool]` - Return MCP tools
- `async handle_tool_call(tool_name: str, arguments: Any) -> Sequence[TextContent]` - Handle tool execution

**Optional Methods:**

- `async on_load()` - Called when module loads
- `async on_unload()` - Called when module unloads
- `validate_environment() -> tuple[bool, str]` - Validate environment
- `get_dependencies() -> List[str]` - List module dependencies

**Properties:**

- `flipper: FlipperClient` - Flipper client instance
- `enabled: bool` - Whether module is enabled

## BadUSB Module API

### BadUSBModule

BadUSB keyboard emulation module.

```python
from flipper_mcp.modules.badusb import BadUSBModule

module = BadUSBModule(flipper_client)
```

**Tools:**

#### badusb_list

List all BadUSB scripts.

```python
# No parameters
result = await module.handle_tool_call("badusb_list", {})
```

**Returns:** List of script filenames

#### badusb_read

Read script contents.

```python
result = await module.handle_tool_call("badusb_read", {
    "filename": "test.txt"
})
```

**Parameters:**

- `filename: str` - Script filename

**Returns:** Script contents

#### badusb_generate

Generate DuckyScript from description.

```python
result = await module.handle_tool_call("badusb_generate", {
    "description": "open notepad and type hello",
    "target_os": "windows",
    "filename": "demo.txt"
})
```

**Parameters:**

- `description: str` - What the script should do
- `target_os: str` - Target OS ("windows", "macos", "linux")
- `filename: str` - Output filename

**Returns:** Generated script

#### badusb_execute

Execute a script (requires confirmation).

```python
result = await module.handle_tool_call("badusb_execute", {
    "filename": "test.txt",
    "confirm": True
})
```

**Parameters:**

- `filename: str` - Script to execute
- `confirm: bool` - Must be true (safety)

**Returns:** Execution result

#### badusb_workflow

Complete workflow (generate + validate + save).

```python
result = await module.handle_tool_call("badusb_workflow", {
    "description": "open calculator",
    "target_os": "windows",
    "execute": False
})
```

**Parameters:**

- `description: str` - What to do
- `target_os: str` - Target OS
- `execute: bool` - Execute after generation

**Returns:** Workflow result

### DuckyScriptGenerator

Generate DuckyScript payloads.

```python
from flipper_mcp.modules.badusb.generator import DuckyScriptGenerator

generator = DuckyScriptGenerator()
script = generator.generate("open notepad", "windows")
```

**Methods:**

- `generate(description: str, target_os: str = "windows") -> str` - Generate script

### ScriptValidator

Validate scripts for safety.

```python
from flipper_mcp.modules.badusb.validator import ScriptValidator

validator = ScriptValidator()
is_valid, error = validator.validate(script)
```

**Methods:**

- `validate(script: str) -> tuple[bool, str]` - Validate script
- `sanitize(script: str) -> str` - Remove dangerous commands

## Utilities

### sanitize_filename()

Sanitize filename to prevent path traversal.

```python
from flipper_mcp.core.utils import sanitize_filename

safe_name = sanitize_filename("../../../etc/passwd")
# Returns: "_.._.._.._etc_passwd"
```

### validate_path()

Validate path is within base directory.

```python
from flipper_mcp.core.utils import validate_path

is_valid = validate_path("/ext/badusb/script.txt", "/ext/badusb")
# Returns: True
```

### format_error()

Format exception for display.

```python
from flipper_mcp.core.utils import format_error

message = format_error(exception)
# Returns: "❌ Error: ValueError: Invalid input"
```

### truncate_text()

Truncate text to maximum length.

```python
from flipper_mcp.core.utils import truncate_text

short = truncate_text(long_text, max_length=100)
```

## MCP Types

### Tool

MCP tool definition.

```python
from mcp.types import Tool

tool = Tool(
    name="mymodule_action",
    description="What this tool does",
    inputSchema={
        "type": "object",
        "properties": {
            "param": {"type": "string"}
        },
        "required": ["param"]
    }
)
```

### TextContent

Text content response.

```python
from mcp.types import TextContent

response = TextContent(
    type="text",
    text="Operation successful"
)
```

## Configuration

### Server Configuration

```yaml
transport:
  type: usb  # or wifi, bluetooth
  
  usb:
    port: /dev/ttyACM0
    baudrate: 115200
  
  wifi:
    host: 192.168.1.1
    port: 8080
  
  bluetooth:
    address: null

modules:
  badusb:
    enabled: true
    config:
      default_os: windows
```

## Error Handling

### Standard Error Response

```python
from mcp.types import TextContent

def handle_error(e: Exception) -> Sequence[TextContent]:
    return [TextContent(
        type="text",
        text=f"❌ Error: {str(e)}"
    )]
```

### Module-Specific Errors

```python
class ModuleError(Exception):
    """Base exception for module errors."""
    pass

class ValidationError(ModuleError):
    """Validation failed."""
    pass
```

## Testing

### Module Testing

```python
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.fixture
def mock_flipper():
    client = Mock()
    client.storage = Mock()
    client.storage.list = AsyncMock(return_value=["test.txt"])
    return client

@pytest.mark.asyncio
async def test_module(mock_flipper):
    module = MyModule(mock_flipper)
    result = await module.handle_tool_call("tool_name", {})
    assert result is not None
```

## Examples

See the [examples](../examples/) directory for complete examples:

- `minimal_module` - Simplest possible module
- `advanced_module` - Full-featured module (coming soon)
- `community_template` - Template for community modules (coming soon)

## CLI

### flipper-mcp

Main CLI command.

```bash
# Start server
flipper-mcp

# Or using Python module
python -m flipper_mcp.cli.main
```

## Environment Variables

- `FLIPPER_PORT` - Override USB port
- `FLIPPER_TRANSPORT` - Override transport type
- `FLIPPER_DEBUG` - Enable debug mode

## See Also

- [Architecture Overview](architecture.md)
- [Module Development Guide](module_development.md)
- [Contributing Guide](../CONTRIBUTING.md)
- [README](../README.md)
