# Architecture Overview

## System Design

Flipper Zero MCP follows a **modular plugin architecture** inspired by Flipper's FAP (Flipper Application Package) system. The core principle is **separation of concerns**: the core handles protocol and infrastructure, while modules provide functionality.

## Components

### 1. Core Layer

The core provides infrastructure services:

```
core/
├── server.py          # MCP protocol handler
├── registry.py        # Module discovery and management
├── flipper_client.py  # RPC client abstraction
├── transport/         # Connection layer
│   ├── base.py       # Abstract transport interface
│   ├── usb.py        # USB serial implementation
│   ├── wifi.py       # WiFi (ESP32) implementation
│   └── bluetooth.py  # BLE implementation
└── utils.py          # Shared utilities
```

**Responsibilities:**
- MCP protocol communication (stdio)
- Module lifecycle management
- Transport abstraction
- Tool routing
- Error handling

**Key Principle:** The core never knows about specific module implementations.

### 2. Module Layer

Modules are self-contained plugins:

```
modules/
├── base_module.py    # Abstract module interface
├── badusb/          # BadUSB module (example)
│   ├── module.py    # Module implementation
│   ├── generator.py # DuckyScript generator
│   ├── validator.py # Safety validator
│   └── templates/   # Script templates
└── [your_module]/   # Your custom module
```

**Module Interface:**
```python
class FlipperModule(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    
    @abstractmethod
    def get_tools(self) -> List[Tool]: ...
    
    @abstractmethod
    async def handle_tool_call(self, tool_name: str, arguments: Any): ...
```

### 3. Transport Layer

Abstracts communication with Flipper Zero:

```python
class FlipperTransport(ABC):
    async def connect(self) -> bool: ...
    async def send(self, data: bytes) -> None: ...
    async def receive(self) -> bytes: ...
```

**Implementations:**
- **USB**: Serial port communication
- **WiFi**: TCP/IP over ESP32 Dev Board
- **Bluetooth**: BLE (future)

## Data Flow

### Tool Execution Flow

```
1. AI Assistant
   │
   └──> MCP Protocol (stdio)
        │
        └──> Core Server
             │
             ├──> Tool Routing (registry)
             │    │
             │    └──> Module.handle_tool_call()
             │         │
             │         └──> Flipper Client
             │              │
             │              └──> Transport Layer
             │                   │
             │                   └──> Flipper Zero Hardware
             │
             └──> Response
                  │
                  └──> MCP Protocol
                       │
                       └──> AI Assistant
```

### Module Discovery Flow

```
1. Server Startup
   │
   └──> Module Registry
        │
        ├──> Scan modules/ directory
        │
        ├──> For each package:
        │    ├──> Import module.py
        │    ├──> Find FlipperModule subclasses
        │    └──> Instantiate module
        │
        ├──> Validate environment
        │
        ├──> Check dependencies
        │
        └──> Register module
             │
             └──> Call module.on_load()
```

## Module Lifecycle

```
┌─────────────────┐
│   Discovery     │  Registry scans for modules
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Registration   │  Instantiate and validate
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Loading      │  Call on_load()
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     Active      │  Handle tool calls
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Unloading     │  Call on_unload()
└─────────────────┘
```

## Module Communication

Modules can access:

1. **Flipper Client**
   ```python
   self.flipper.storage.list("/path")
   self.flipper.app.launch("BadUsb", script_path)
   ```

2. **Other Modules** (via registry)
   ```python
   storage_module = self.registry.get_module("storage")
   ```

3. **Configuration**
   ```python
   self.config = config.get("mymodule", {})
   ```

## Security Model

### Safety Layers

1. **Input Validation**
   - Schema validation (MCP)
   - Type checking
   - Range validation

2. **Module Validation**
   - Environment checks
   - Dependency verification
   - Safety validators (e.g., BadUSB script validation)

3. **Confirmation Flags**
   - Dangerous operations require `confirm=true`
   - Double-check before execution

### Example: BadUSB Safety

```python
# 1. Generate script
script = generator.generate(description, target_os)

# 2. Validate for safety
is_valid, error = validator.validate(script)
if not is_valid:
    return error

# 3. Require confirmation for execution
if not arguments.get("confirm", False):
    return "Execution blocked - confirm required"

# 4. Execute
await flipper.app.launch("BadUsb", script_path)
```

## Extension Points

### Adding New Transports

```python
from flipper_mcp.core.transport.base import FlipperTransport

class MyTransport(FlipperTransport):
    async def connect(self) -> bool: ...
    async def send(self, data: bytes) -> None: ...
    async def receive(self) -> bytes: ...

# Register in transport/__init__.py
TRANSPORTS["mytransport"] = MyTransport
```

### Adding New Modules

1. Create module directory
2. Implement `FlipperModule` interface
3. Export from `__init__.py`
4. Restart server → Auto-discovered!

### Custom Validators

```python
class MyValidator:
    def validate(self, data: Any) -> tuple[bool, str]:
        # Your validation logic
        return is_valid, error_message
```

## Configuration

### Server Configuration

```yaml
transport:
  type: usb
  usb:
    port: /dev/ttyACM0
    baudrate: 115200

modules:
  badusb:
    enabled: true
    config:
      default_os: windows
```

### Module Configuration

Modules can read their config:

```python
class MyModule(FlipperModule):
    def __init__(self, flipper_client, config=None):
        self.config = config or {}
        self.setting = self.config.get("my_setting", "default")
```

## Performance Considerations

### Async Architecture

- All I/O is async
- Non-blocking transport operations
- Concurrent tool execution

### Caching

```python
from functools import lru_cache

@lru_cache(maxsize=128)
async def expensive_operation(self, param):
    # Cached results
    pass
```

### Resource Management

- Connection pooling (future)
- Lazy module loading (future)
- Memory limits (future)

## Testing Strategy

### Unit Tests

Test individual components in isolation:

```python
@pytest.mark.asyncio
async def test_module_tool():
    mock_flipper = Mock()
    module = MyModule(mock_flipper)
    result = await module.handle_tool_call("tool", {})
    assert result is not None
```

### Integration Tests

Test with real Flipper hardware:

```python
@pytest.mark.integration
@pytest.mark.skipif(not has_flipper(), reason="No Flipper")
async def test_with_hardware():
    # Test with actual device
    pass
```

## Future Enhancements

### Planned Features

1. **Hot Module Reloading**
   - Reload modules without restarting
   - Development mode with auto-reload

2. **Module Marketplace**
   - Central registry of community modules
   - Version management
   - Dependency resolution

3. **Permission System**
   - Fine-grained access control
   - User approval for dangerous operations

4. **Event System**
   - Modules emit/subscribe to events
   - Inter-module communication

5. **Web UI**
   - Visual module management
   - Real-time monitoring
   - Script editor

## References

- [MCP Protocol](https://github.com/modelcontextprotocol)
- [Flipper Zero](https://flipperzero.one/)
- [Python Async](https://docs.python.org/3/library/asyncio.html)
