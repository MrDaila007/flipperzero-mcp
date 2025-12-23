# Flipper Zero MCP Server

**Modular, extensible Model Context Protocol (MCP) server for Flipper Zero**

Control your Flipper Zero hardware hacking tool through AI assistants using natural language. Built with a modular architecture inspired by Flipper's FAP (Flipper Application Package) system - extend capabilities without modifying core code.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

## 🌟 Features

- **🔌 Modular Architecture**: Add new capabilities through independent modules
- **🤖 AI-Powered**: Generate DuckyScript from natural language descriptions
- **🔒 Safety First**: Built-in validation and safety checks
- **📡 Multi-Transport**: USB, WiFi (ESP32), and Bluetooth support
- **🎯 BadUSB Module**: Full keyboard/mouse emulation (Phase 1)
- **🔧 Developer Friendly**: Simple module API for community contributions

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Usage](#-usage)
- [Architecture](#-architecture)
- [Available Modules](#-available-modules)
- [Creating Modules](#-creating-modules)
- [Contributing](#-contributing)
- [License](#-license)

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python -m flipper_mcp.cli.main

# Or use the CLI command (after pip install -e .)
flipper-mcp
```

The server will:
1. Auto-detect Flipper Zero on USB
2. Discover and load available modules
3. Start MCP server for AI assistant connections

## 📦 Installation

### Prerequisites

- Python 3.10 or higher
- Flipper Zero device (for hardware operations)
- USB cable or WiFi Dev Board (for connectivity)

### Install from Source

```bash
git clone https://github.com/busse/flipperzero-mcp.git
cd flipperzero-mcp

# Install in development mode
pip install -e .

# Or install dependencies only
pip install -r requirements.txt
```

### Configuration

Create a `config.yaml` (optional - defaults work for most cases):

```yaml
transport:
  type: usb  # or wifi, bluetooth
  
  usb:
    port: /dev/ttyACM0  # Auto-detected if not specified
    baudrate: 115200
  
  wifi:
    host: 192.168.1.1
    port: 8080
```

## 💡 Usage

### With AI Assistants (Claude, etc.)

Once the server is running, connect it to your AI assistant. Example interactions:

**Natural Language → BadUSB Scripts:**
```
You: "Create a BadUSB script that opens notepad and types hello world on Windows"
Assistant: [Uses badusb_generate tool]
Result: ✅ Script generated, validated, and saved to Flipper
```

**List Scripts:**
```
You: "What BadUSB scripts do I have?"
Assistant: [Uses badusb_list tool]
Result: Shows all scripts on Flipper Zero
```

**Complete Workflow:**
```
You: "Generate a script to open calculator on Windows, validate it, and save it"
Assistant: [Uses badusb_workflow tool]
Result: Complete workflow with validation and safety checks
```

### Available Tools

#### BadUSB Module

- `badusb_list` - List all scripts on Flipper Zero
- `badusb_read` - Read script contents
- `badusb_generate` - Generate DuckyScript from description
- `badusb_execute` - Execute a script (requires confirmation)
- `badusb_workflow` - Complete generate→validate→save workflow

## 🏗️ Architecture

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
│  └────────────────────────────────────────────────────────┘ │
│                            ▲                                 │
│                            │ Module API                      │
│       ┌────────────────────┼────────────────────┐           │
│       │                    │                    │           │
│  ┌────▼─────┐  ┌──────────▼───┐  ┌────────────▼────┐      │
│  │  BadUSB  │  │   Sub-GHz    │  │      NFC        │      │
│  │  Module  │  │   Module     │  │    Module       │      │
│  │ ✅ Done  │  │  (Future)    │  │   (Future)      │      │
│  └──────────┘  └──────────────┘  └─────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Key Principles

- **Self-contained modules**: Each module is independent
- **Zero core modifications**: Add features without touching core code
- **Auto-discovery**: Modules are automatically found and loaded
- **Type-safe**: Full type hints throughout

## 📚 Available Modules

### BadUSB (v1.0.0) ✅

Keyboard/mouse emulation with AI-powered script generation.

**Features:**
- Natural language → DuckyScript conversion
- Multi-OS support (Windows, macOS, Linux)
- Safety validation
- Script management (list, read, write)
- Execution with confirmation

**Example:**
```python
# The AI assistant can do:
badusb_generate(
    description="Open calculator on Windows",
    target_os="windows",
    filename="calc.txt"
)
```

### Coming Soon

- **Sub-GHz Module** - Radio signal capture and transmission
- **NFC Module** - Card reading and emulation
- **RFID Module** - RFID operations
- **Infrared Module** - IR remote control

## 🔧 Creating Modules

### Quick Start

1. Create module structure:
```bash
mkdir -p src/flipper_mcp/modules/mymodule
cd src/flipper_mcp/modules/mymodule
touch __init__.py module.py
```

2. Implement the module:

```python
# module.py
from typing import List, Any, Sequence
from mcp.types import Tool, TextContent
from ..base_module import FlipperModule

class MyModule(FlipperModule):
    @property
    def name(self) -> str:
        return "mymodule"
    
    @property
    def version(self) -> str:
        return "0.1.0"
    
    @property
    def description(self) -> str:
        return "My custom module"
    
    def get_tools(self) -> List[Tool]:
        return [
            Tool(
                name="mymodule_action",
                description="Does something cool",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "param": {"type": "string"}
                    },
                    "required": ["param"]
                }
            )
        ]
    
    async def handle_tool_call(
        self, tool_name: str, arguments: Any
    ) -> Sequence[TextContent]:
        if tool_name == "mymodule_action":
            result = f"Executed with: {arguments['param']}"
            return [TextContent(type="text", text=result)]
        
        return [TextContent(type="text", text=f"Unknown tool: {tool_name}")]
```

3. Export the module:

```python
# __init__.py
from .module import MyModule
__all__ = ['MyModule']
```

4. Restart the server - your module is auto-discovered! 🎉

### Module Development Guide

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Detailed module API reference
- Best practices
- Testing guidelines
- Security considerations
- Example modules

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/modules/test_badusb.py

# Run with coverage
pytest --cov=flipper_mcp
```

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Code of conduct
- Development setup
- Pull request process
- Module submission guidelines

### Ways to Contribute

- 🐛 Report bugs
- 💡 Suggest features
- 📝 Improve documentation
- 🔧 Create new modules
- ✅ Add tests

## 📖 Documentation

- [Architecture Overview](docs/architecture.md)
- [Module Development Guide](docs/module_development.md)
- [API Reference](docs/api_reference.md)
- [Transport Guide](docs/transport_guide.md)

## 🔒 Security

This tool can perform hardware operations. Please:
- Review all generated scripts before execution
- Use the built-in validation
- Never disable safety checks
- Report security issues privately

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Flipper Zero team for the amazing hardware
- MCP protocol for AI-tool integration
- Community contributors

## 📞 Support

- 🐛 [Issues](https://github.com/busse/flipperzero-mcp/issues)
- 💬 [Discussions](https://github.com/busse/flipperzero-mcp/discussions)
- 📧 Email: [Create an issue for support]

## 🚧 Project Status

**Phase 1: Core + BadUSB** ✅ Complete
- [x] Core architecture
- [x] Module system
- [x] Transport abstraction
- [x] BadUSB module

**Phase 2: Extended Modules** 🚧 Planned
- [ ] Sub-GHz module
- [ ] NFC module
- [ ] RFID module
- [ ] Infrared module

**Phase 3: Ecosystem** 🔮 Future
- [ ] Module marketplace
- [ ] Web UI
- [ ] Advanced workflows
- [ ] Community templates

---

**Built with ❤️ for the Flipper Zero community**
