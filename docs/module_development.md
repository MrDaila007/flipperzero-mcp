# Module Development Guide

Complete guide to creating modules for Flipper Zero MCP.

## Quick Start

The fastest way to create a module:

```bash
# 1. Create module directory
mkdir -p src/flipper_mcp/modules/mymodule

# 2. Create files
cd src/flipper_mcp/modules/mymodule
touch __init__.py module.py

# 3. Implement (see template below)

# 4. Test
python -m flipper_mcp.cli.main
```

## Module Template

### Minimal Module

```python
# src/flipper_mcp/modules/mymodule/module.py

from typing import List, Any, Sequence
from mcp.types import Tool, TextContent
from ..base_module import FlipperModule

class MyModule(FlipperModule):
    """One-line module description."""
    
    @property
    def name(self) -> str:
        return "mymodule"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Brief description of what this module does"
    
    def get_tools(self) -> List[Tool]:
        return [
            Tool(
                name="mymodule_action",
                description="What this tool does",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "param": {
                            "type": "string",
                            "description": "Parameter description"
                        }
                    },
                    "required": ["param"]
                }
            )
        ]
    
    async def handle_tool_call(
        self, tool_name: str, arguments: Any
    ) -> Sequence[TextContent]:
        if tool_name == "mymodule_action":
            param = arguments["param"]
            result = f"Executed with: {param}"
            return [TextContent(type="text", text=result)]
        
        return [TextContent(
            type="text",
            text=f"Unknown tool: {tool_name}"
        )]
```

### Export Module

```python
# src/flipper_mcp/modules/mymodule/__init__.py

from .module import MyModule

__all__ = ['MyModule']
```

## Module Interface

### Required Properties

#### `name` Property

```python
@property
def name(self) -> str:
    """
    Unique module identifier.
    
    Rules:
    - Lowercase
    - No spaces (use underscores)
    - Descriptive
    - Unique across all modules
    
    Examples: "badusb", "subghz", "nfc"
    """
    return "mymodule"
```

#### `version` Property

```python
@property
def version(self) -> str:
    """
    Semantic version.
    
    Format: MAJOR.MINOR.PATCH
    - MAJOR: Breaking changes
    - MINOR: New features
    - PATCH: Bug fixes
    
    Examples: "1.0.0", "2.1.3"
    """
    return "1.0.0"
```

#### `description` Property

```python
@property
def description(self) -> str:
    """
    One-line description.
    
    Keep it brief and clear.
    Shown in module listings.
    """
    return "Handles XYZ operations on Flipper Zero"
```

### Required Methods

#### `get_tools()` Method

```python
def get_tools(self) -> List[Tool]:
    """
    Return list of MCP tools.
    
    Each tool:
    - Has unique name: {module}_{action}
    - Clear description
    - JSON schema for parameters
    """
    return [
        Tool(
            name="mymodule_read",
            description="Read data from Flipper",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to read"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="mymodule_write",
            description="Write data to Flipper",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "data": {"type": "string"}
                },
                "required": ["path", "data"]
            }
        )
    ]
```

#### `handle_tool_call()` Method

```python
async def handle_tool_call(
    self, tool_name: str, arguments: Any
) -> Sequence[TextContent]:
    """
    Execute a tool.
    
    Args:
        tool_name: Name of the tool
        arguments: Dict of arguments
    
    Returns:
        List of TextContent responses
    """
    if tool_name == "mymodule_read":
        return await self._read(arguments["path"])
    
    elif tool_name == "mymodule_write":
        return await self._write(
            arguments["path"],
            arguments["data"]
        )
    
    # Unknown tool
    return [TextContent(
        type="text",
        text=f"Error: Unknown tool '{tool_name}'"
    )]
```

### Optional Methods

#### Lifecycle Hooks

```python
async def on_load(self) -> None:
    """
    Called when module is loaded.
    
    Use for:
    - Initialization
    - Resource allocation
    - Configuration loading
    """
    print(f"{self.name} loaded!")
    self.cache = {}

async def on_unload(self) -> None:
    """
    Called when module is unloaded.
    
    Use for:
    - Cleanup
    - Resource deallocation
    - Saving state
    """
    self.cache.clear()
    print(f"{self.name} unloaded!")
```

#### Environment Validation

```python
def validate_environment(self) -> tuple[bool, str]:
    """
    Check if module can run.
    
    Returns:
        (is_valid, error_message)
    
    Check for:
    - Firmware version
    - Required apps
    - System capabilities
    """
    # Example: Check firmware version
    # version = get_firmware_version()
    # if version < required_version:
    #     return False, f"Requires firmware >= {required_version}"
    
    return True, ""
```

#### Dependencies

```python
def get_dependencies(self) -> List[str]:
    """
    List required modules.
    
    Registry ensures dependencies are loaded first.
    """
    return ["storage", "system"]
```

## Tool Design

### Tool Naming

**Format:** `{module}_{action}`

**Examples:**
- ✅ `badusb_generate`
- ✅ `subghz_scan`
- ✅ `nfc_read`
- ❌ `generate` (too generic)
- ❌ `BadUSB_Generate` (wrong case)

### Input Schema

Use JSON Schema for parameters:

```python
inputSchema={
    "type": "object",
    "properties": {
        "filename": {
            "type": "string",
            "description": "Name of the file",
            "pattern": "^[a-zA-Z0-9_-]+\\.txt$"
        },
        "mode": {
            "type": "string",
            "enum": ["read", "write", "append"],
            "default": "read"
        },
        "confirm": {
            "type": "boolean",
            "description": "Confirm dangerous operation",
            "default": False
        }
    },
    "required": ["filename"]
}
```

### Response Format

Return clear, formatted responses:

```python
# Success
result = "✅ Operation successful\n\n"
result += "Details:\n"
result += f"  • Files processed: 5\n"
result += f"  • Time taken: 2.3s\n"
return [TextContent(type="text", text=result)]

# Error
error = "❌ Operation failed: File not found\n\n"
error += "Tried: /ext/badusb/script.txt\n"
error += "Available files:\n"
error += "  • test1.txt\n"
error += "  • test2.txt\n"
return [TextContent(type="text", text=error)]
```

## Flipper Client API

### Storage Operations

```python
# List files
files = await self.flipper.storage.list("/ext/badusb")

# Read file
content = await self.flipper.storage.read("/ext/badusb/script.txt")

# Write file
await self.flipper.storage.write("/ext/badusb/new.txt", "content")

# Delete file
await self.flipper.storage.delete("/ext/badusb/old.txt")

# Create directory
await self.flipper.storage.mkdir("/ext/mymodule")
```

### App Operations

```python
# Launch app
success = await self.flipper.app.launch("BadUsb", "/ext/badusb/script.txt")

# Stop app
await self.flipper.app.stop("BadUsb")
```

### Device Info

```python
# Get firmware version
version = await self.flipper.get_firmware_version()

# Get device info
info = await self.flipper.get_device_info()
```

## Best Practices

### 1. Input Validation

```python
async def handle_tool_call(self, tool_name: str, arguments: Any):
    # Validate parameters
    filename = arguments.get("filename")
    if not filename:
        return [TextContent(
            type="text",
            text="Error: filename is required"
        )]
    
    # Sanitize inputs
    from flipper_mcp.core.utils import sanitize_filename
    filename = sanitize_filename(filename)
    
    # Proceed with operation
    ...
```

### 2. Error Handling

```python
async def handle_tool_call(self, tool_name: str, arguments: Any):
    try:
        result = await self._perform_operation(arguments)
        return [TextContent(type="text", text=result)]
    
    except FileNotFoundError as e:
        return [TextContent(
            type="text",
            text=f"❌ File not found: {e}"
        )]
    
    except Exception as e:
        return [TextContent(
            type="text",
            text=f"❌ Unexpected error: {e}"
        )]
```

### 3. Safety Checks

```python
async def handle_tool_call(self, tool_name: str, arguments: Any):
    if tool_name == "mymodule_delete_all":
        # Require confirmation
        if not arguments.get("confirm", False):
            return [TextContent(
                type="text",
                text="⚠️  This is dangerous! Set confirm=true to proceed"
            )]
        
        # Double-check
        count = await self._count_files()
        if count > 100:
            return [TextContent(
                type="text",
                text=f"⚠️  Too many files ({count}). Manual deletion required."
            )]
        
        # Proceed with operation
        ...
```

### 4. Progress Feedback

```python
async def handle_tool_call(self, tool_name: str, arguments: Any):
    result = "🔄 Processing...\n\n"
    
    # Step 1
    result += "Step 1: Scanning files... "
    files = await self._scan_files()
    result += f"✓ Found {len(files)}\n"
    
    # Step 2
    result += "Step 2: Processing each file...\n"
    for i, file in enumerate(files, 1):
        result += f"  [{i}/{len(files)}] {file}... "
        await self._process_file(file)
        result += "✓\n"
    
    result += "\n✅ Complete!"
    return [TextContent(type="text", text=result)]
```

## Advanced Features

### Caching

```python
from functools import lru_cache

class MyModule(FlipperModule):
    def __init__(self, flipper_client):
        super().__init__(flipper_client)
        self._cache = {}
    
    async def _get_data(self, key: str) -> Any:
        # Check cache
        if key in self._cache:
            return self._cache[key]
        
        # Fetch from Flipper
        data = await self.flipper.storage.read(f"/data/{key}")
        
        # Cache for next time
        self._cache[key] = data
        return data
```

### Configuration

```python
class MyModule(FlipperModule):
    def __init__(self, flipper_client, config=None):
        super().__init__(flipper_client)
        self.config = config or {}
        
        # Read settings
        self.timeout = self.config.get("timeout", 30)
        self.max_retries = self.config.get("max_retries", 3)
```

### Helpers

Create helper classes:

```python
# mymodule/parser.py
class DataParser:
    def parse(self, data: str) -> dict:
        # Parsing logic
        pass

# mymodule/module.py
from .parser import DataParser

class MyModule(FlipperModule):
    def __init__(self, flipper_client):
        super().__init__(flipper_client)
        self.parser = DataParser()
```

## Testing Your Module

### Unit Test Example

```python
# tests/modules/test_mymodule.py

import pytest
from unittest.mock import Mock, AsyncMock
from flipper_mcp.modules.mymodule import MyModule

@pytest.fixture
def mock_flipper():
    client = Mock()
    client.storage = Mock()
    client.storage.list = AsyncMock(return_value=["file1.txt", "file2.txt"])
    return client

@pytest.mark.asyncio
async def test_mymodule_list(mock_flipper):
    module = MyModule(mock_flipper)
    
    result = await module.handle_tool_call("mymodule_list", {})
    
    assert len(result) == 1
    assert "file1.txt" in result[0].text
    assert "file2.txt" in result[0].text
```

### Manual Testing

```bash
# Start server
python -m flipper_mcp.cli.main

# In another terminal, test with MCP client
# or use AI assistant to call tools
```

## Publishing Your Module

### Option 1: Standalone Package

Create separate repository:

```
my-flipper-module/
├── pyproject.toml
├── README.md
├── src/
│   └── flipper_mcp_mymodule/
│       ├── __init__.py
│       └── module.py
└── tests/
```

Users install with:
```bash
pip install flipper-mcp-mymodule
```

### Option 2: Submit to Main Repo

1. Fork the repository
2. Add your module to `src/flipper_mcp/modules/`
3. Add tests
4. Update documentation
5. Submit pull request

## Checklist

Before submitting your module:

- [ ] Follows naming conventions
- [ ] Has clear docstrings
- [ ] Implements all required methods
- [ ] Validates inputs
- [ ] Handles errors gracefully
- [ ] Has safety checks (if needed)
- [ ] Includes unit tests
- [ ] Updates documentation
- [ ] No external dependencies (or documented)

## Resources

- [BadUSB Module](../src/flipper_mcp/modules/badusb/) - Reference implementation
- [Base Module](../src/flipper_mcp/modules/base_module.py) - Interface definition
- [Module Registry](../src/flipper_mcp/core/registry.py) - Discovery system
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines

## Getting Help

- 💬 [Discussions](https://github.com/busse/flipperzero-mcp/discussions)
- 🐛 [Issues](https://github.com/busse/flipperzero-mcp/issues)
- 📖 [Documentation](../docs/)

Happy module building! 🎉
