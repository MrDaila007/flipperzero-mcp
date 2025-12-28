# WiFi Dev Board: Protobuf RPC over WiFi

This guide provides a comprehensive architectural reference and implementation guide for using the Flipper Zero WiFi Dev Board with this MCP server. The WiFi Dev Board enables wireless control of your Flipper Zero device over a WiFi network using Protobuf RPC, eliminating the need for USB connections after initial setup.

## Table of Contents

1. [Overview](#overview)
2. [Hardware Requirements](#hardware-requirements)
3. [WiFi Dev Board Architecture](#wifi-dev-board-architecture)
4. [Firmware Setup](#firmware-setup)
5. [Network Architecture](#network-architecture)
6. [Communication Flow](#communication-flow)
7. [Protobuf RPC Protocol](#protobuf-rpc-protocol)
8. [Complete Example: Music Player Lifecycle](#complete-example-music-player-lifecycle)
9. [Implementation Guide](#implementation-guide)
10. [Code Patterns](#code-patterns)
11. [Troubleshooting](#troubleshooting)
12. [References](#references)

---

## Overview

The Flipper Zero WiFi Dev Board is an ESP32-based expansion module that provides wireless connectivity to your Flipper Zero. This project implements a custom firmware approach that enables:

- **Wireless Protobuf RPC**: Full protobuf-based communication over WiFi
- **No USB Required**: Control Flipper Zero entirely over network after setup
- **MCP Integration**: Seamless integration with Model Context Protocol servers
- **Full API Access**: Complete access to Flipper Zero's RPC API over WiFi

### Key Components

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   MCP Client    │         │  WiFi Dev Board  │         │  Flipper Zero   │
│ (Claude/Python) │ ◄─WiFi─►│    (ESP32)       │ ◄─UART─►│    Device       │
│                 │         │  Custom Firmware │         │                 │
└─────────────────┘         └──────────────────┘         └─────────────────┘
```

---

## Hardware Requirements

### Required Hardware

1. **Flipper Zero**: Main device running official firmware
2. **WiFi Dev Board**: ESP32-based WiFi development board
   - Official Flipper Zero WiFi Dev Board, or
   - Compatible ESP32 module with UART connection
3. **Power Supply**: Ensure adequate power for both devices

### WiFi Dev Board Specifications

- **Microcontroller**: ESP32 (Dual-core, WiFi & Bluetooth)
- **Connection**: UART to Flipper Zero GPIO pins
- **Voltage**: 3.3V logic level
- **Communication**: Serial UART at 115200 baud (default)

### Pin Connections

```
Flipper Zero GPIO     WiFi Dev Board (ESP32)
─────────────────     ──────────────────────
TX (GPIO 13/14)  ──►  RX (GPIO 16)
RX (GPIO 13/14)  ◄──  TX (GPIO 17)
GND              ───  GND
3V3              ───  VCC (if powered from Flipper)
```

**Note**: Pin numbers may vary depending on your specific WiFi Dev Board model. Consult your board's documentation.

---

## WiFi Dev Board Architecture

### Component Overview

```
╔════════════════════════════════════════════════════════════════╗
║                     WiFi Dev Board (ESP32)                     ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  ┌──────────────────────────────────────────────────────────┐ ║
║  │              TCP Server (Port 8080)                      │ ║
║  │  - Accepts WiFi connections from MCP clients             │ ║
║  │  - Manages multiple client sessions                      │ ║
║  └────────────────────┬─────────────────────────────────────┘ ║
║                       │                                        ║
║  ┌────────────────────▼─────────────────────────────────────┐ ║
║  │            Bidirectional Buffer/Framing                  │ ║
║  │  - Buffers TCP data → UART                               │ ║
║  │  - Buffers UART data → TCP                               │ ║
║  │  - Preserves protobuf framing (varint-delimited)         │ ║
║  └────────────────────┬─────────────────────────────────────┘ ║
║                       │                                        ║
║  ┌────────────────────▼─────────────────────────────────────┐ ║
║  │              UART Interface (115200 baud)                │ ║
║  │  - TX/RX to Flipper Zero                                 │ ║
║  │  - Transparent data passthrough                          │ ║
║  └──────────────────────────────────────────────────────────┘ ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
                             │
                             ▼
                    ┌─────────────────┐
                    │  Flipper Zero   │
                    │   (UART GPIO)   │
                    └─────────────────┘
```

### Firmware Responsibilities

The WiFi Dev Board firmware acts as a **transparent bridge** between WiFi and UART:

1. **WiFi Server**: Listens for incoming TCP connections
2. **Data Forwarding**: Bidirectionally forwards data between TCP and UART
3. **Frame Preservation**: Maintains protobuf message boundaries
4. **Connection Management**: Handles connect/disconnect events
5. **Configuration**: Manages WiFi credentials and network settings

---

## Firmware Setup

### Flashing the WiFi Dev Board

The WiFi Dev Board requires custom firmware that implements the TCP-to-UART bridge. Here's how to set it up:

#### Option 1: Using Pre-built Firmware (Recommended)

```bash
# Install esptool (if not already installed)
pip install esptool

# Erase existing firmware
esptool.py --port /dev/ttyUSB0 erase_flash

# Flash the WiFi bridge firmware
esptool.py --port /dev/ttyUSB0 --baud 460800 write_flash 0x0 wifi_bridge_firmware.bin
```

#### Option 2: Building from Source

If you're building custom firmware or need modifications:

```bash
# Install PlatformIO
pip install platformio

# Clone firmware repository (example)
git clone https://github.com/esp32-wifi-uart-bridge/firmware.git
cd firmware

# Configure WiFi credentials in platformio.ini or src/config.h
# Edit src/config.h:
#   #define WIFI_SSID "YourNetworkName"
#   #define WIFI_PASSWORD "YourPassword"
#   #define TCP_PORT 8080
#   #define UART_BAUD 115200

# Build and upload
pio run --target upload
```

### WiFi Configuration

After flashing, configure the WiFi Dev Board to connect to your network:

#### Method 1: Hard-coded Configuration

Edit the firmware configuration before building:

```cpp
// src/config.h
#define WIFI_SSID "YourNetworkName"
#define WIFI_PASSWORD "YourPassword"
#define TCP_PORT 8080
#define UART_BAUD 115200
#define UART_RX_PIN 16
#define UART_TX_PIN 17
```

#### Method 2: WiFi Manager (if supported)

Some firmware variants support WiFi Manager for easy configuration:

1. Power on the WiFi Dev Board
2. Look for a WiFi network named "FlipperWiFi" or similar
3. Connect to this network
4. Navigate to `http://192.168.4.1` in your browser
5. Enter your WiFi credentials
6. Save and reboot

### Verifying Connection

Once configured, verify the WiFi Dev Board is on your network:

```bash
# Find the IP address using nmap or your router's admin panel
nmap -sn 192.168.1.0/24 | grep -i esp32

# Or check your router's DHCP leases
# The device should appear with a hostname like "ESP32_XXXXXX"

# Test connectivity
ping 192.168.1.100  # Replace with your device's IP

# Test TCP port
nc -zv 192.168.1.100 8080
```

---

## Network Architecture

### Network Topology

```
                              Internet
                                 │
                                 │
                          ┌──────▼──────┐
                          │   Router    │
                          │ (Gateway)   │
                          └──┬──────┬───┘
                             │      │
                ┌────────────┘      └────────────┐
                │                                 │
                │                                 │
        ┌───────▼────────┐               ┌───────▼────────┐
        │   Computer     │               │ WiFi Dev Board │
        │  (MCP Client)  │               │    (ESP32)     │
        │ 192.168.1.50   │               │ 192.168.1.100  │
        └────────────────┘               └────────┬───────┘
                                                  │
                                                  │ UART
                                                  │
                                         ┌────────▼────────┐
                                         │  Flipper Zero   │
                                         │                 │
                                         └─────────────────┘
```

### IP Configuration

**Static IP (Recommended for production):**

```cpp
// In firmware config
#define USE_STATIC_IP true
#define STATIC_IP IPAddress(192, 168, 1, 100)
#define GATEWAY IPAddress(192, 168, 1, 1)
#define SUBNET IPAddress(255, 255, 255, 0)
```

**DHCP (Easier for testing):**

```cpp
#define USE_STATIC_IP false
```

### Port Configuration

- **Default TCP Port**: 8080
- **UART Baud Rate**: 115200
- **Protocol**: Raw TCP (no TLS in basic implementation)

**Security Note**: For production use, consider implementing TLS/SSL encryption or using a VPN. The basic implementation uses unencrypted TCP.

---

## Communication Flow

### High-Level Overview

This section illustrates the complete end-to-end communication flow from MCP client to Flipper Zero and back.

```
 MCP Client          Network          WiFi Dev Board      Flipper Zero
 (Computer)                              (ESP32)            (Device)
     │                                      │                   │
     │  1. Connect TCP Socket               │                   │
     ├─────────────TCP SYN───────────────►  │                   │
     │  ◄────────TCP SYN-ACK───────────────┤                   │
     │                                      │                   │
     │  2. Send Protobuf RPC Request        │                   │
     ├────[varint][Main message]───────────►│                   │
     │                                      │                   │
     │                                      │  3. Forward UART  │
     │                                      ├──[raw bytes]─────►│
     │                                      │                   │
     │                                      │  4. Process RPC   │
     │                                      │                   │ (RPC Handler)
     │                                      │                   │
     │                                      │  5. UART Response │
     │                                      │ ◄─[raw bytes]─────┤
     │                                      │                   │
     │  6. TCP Response                     │                   │
     │ ◄────[varint][Main message]──────────┤                   │
     │                                      │                   │
     │  7. Process Response                 │                   │
     │  (Update UI, etc.)                   │                   │
     │                                      │                   │
```

### Detailed Communication Sequence

#### Phase 1: Connection Establishment

```python
# Step 1: MCP Client establishes WiFi connection
import asyncio

async def connect_to_flipper():
    """Connect to Flipper Zero via WiFi Dev Board."""
    # TCP connection to WiFi Dev Board
    reader, writer = await asyncio.open_connection(
        host='192.168.1.100',  # WiFi Dev Board IP
        port=8080
    )
    
    # The WiFi Dev Board is now bridging to Flipper UART
    return reader, writer
```

#### Phase 2: RPC Session Initialization

```python
# Step 2: Initialize RPC session on the UART transport
async def initialize_rpc_session(writer, reader):
    """Start RPC session mode on Flipper Zero."""
    # Send CLI command to enter RPC mode
    # (Flipper CDC UART starts in CLI mode)
    writer.write(b'start_rpc_session\r')
    await writer.drain()
    
    # Drain CLI banner/response
    await asyncio.sleep(0.3)
    try:
        _ = await asyncio.wait_for(reader.read(4096), timeout=0.5)
    except asyncio.TimeoutError:
        pass  # Expected - no more data
    
    # Now in RPC mode - ready for protobuf messages
```

#### Phase 3: Protobuf Message Exchange

```python
# Step 3: Send protobuf RPC request
async def send_rpc_request(writer, reader):
    """Send a protobuf RPC request and get response."""
    from flipper_mcp.core.protobuf_gen import flipper_pb2, system_pb2
    
    # Build protobuf request
    main = flipper_pb2.Main()
    main.command_id = 1
    main.has_next = False
    main.command_status = flipper_pb2.CommandStatus.OK
    
    # System info request example
    main.system_info_request.CopyFrom(system_pb2.SystemInfoRequest())
    
    # Serialize to bytes
    message_bytes = main.SerializeToString()
    
    # Encode with varint length prefix (nanopb delimited framing)
    length_varint = encode_varint(len(message_bytes))
    
    # Send framed message
    writer.write(length_varint + message_bytes)
    await writer.drain()
    
    # Receive response (framed)
    response_length = await read_varint(reader)
    response_bytes = await reader.readexactly(response_length)
    
    # Parse response
    response = flipper_pb2.Main()
    response.ParseFromString(response_bytes)
    
    return response
```

### Data Framing

The WiFi Dev Board **must preserve** the protobuf framing. Each message uses nanopb delimited framing:

```
┌─────────────┬──────────────────────────────┐
│ Varint Len  │   Protobuf Message Bytes     │
│  (1-5 bytes)│   (Length = Varint value)    │
└─────────────┴──────────────────────────────┘

Example:
  [0x0A] [0x08, 0x12, 0x06, 0x08, 0x01, 0x10, 0x02, 0x18, 0x03, 0x20, 0x04]
   ^^^^   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   Len=10           Protobuf message (10 bytes)
```

**Critical**: The ESP32 firmware must **not** buffer or process the varint framing - it should transparently forward bytes between TCP and UART to preserve message boundaries.

---

## Protobuf RPC Protocol

### Protocol Specification

The Flipper Zero RPC protocol is based on Protocol Buffers (protobuf) as defined in the official repository:

- **Repository**: [flipperdevices/flipperzero-protobuf](https://github.com/flipperdevices/flipperzero-protobuf)
- **Version**: Compatible with official firmware releases
- **Framing**: Nanopb delimited (varint length prefix)

### Message Structure

Every RPC message follows this structure:

```protobuf
// From flipper.proto
message Main {
    uint32 command_id = 1;      // Unique command identifier
    CommandStatus command_status = 2;  // OK, ERROR, etc.
    bool has_next = 3;          // More messages in sequence
    
    oneof content {
        // System commands
        SystemPingRequest system_ping_request = 4;
        SystemPingResponse system_ping_response = 5;
        // ... many more message types ...
        
        // Storage commands
        StorageListRequest storage_list_request = 10;
        StorageReadRequest storage_read_request = 11;
        // ...
        
        // Application commands
        AppStartRequest app_start_request = 20;
        // ...
    }
}
```

### Command Flow

```
Client                          Flipper Zero
  │                                  │
  │  Main {                          │
  │    command_id: 1                 │
  │    storage_read_request {        │
  │      path: "/ext/file.txt"       │
  │    }                             │
  │  }                               │
  ├─────────────────────────────────►│
  │                                  │
  │                                  │ (Read file from SD card)
  │                                  │
  │  Main {                          │
  │    command_id: 1                 │
  │    command_status: OK            │
  │    storage_read_response {       │
  │      file { data: "content..." } │
  │    }                             │
  │  }                               │
  │◄─────────────────────────────────┤
  │                                  │
```

### Available RPC Commands

The following command categories are available (see proto/ for complete definitions):

- **System**: Ping, reboot, device info, power info
- **Storage**: List, read, write, delete, mkdir, stat
- **Application**: Start app, load file, get error
- **GPIO**: Set mode, write, read
- **Property**: Get system properties
- **Desktop**: Lock/unlock status

### Implementation in Python

This project includes generated Python protobuf code in `src/flipper_mcp/core/protobuf_gen/`:

```python
from flipper_mcp.core.protobuf_gen import (
    flipper_pb2,      # Main message definitions
    system_pb2,       # System commands
    storage_pb2,      # Storage commands
    application_pb2,  # App commands
    property_pb2,     # Property commands
)
```

---

## Complete Example: Music Player Lifecycle

This section provides a complete, detailed walkthrough of using the Music Player module over WiFi, demonstrating the full lifecycle from connection to playback.

### Architecture: Music Player Over WiFi

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         Complete System Architecture                     │
└──────────────────────────────────────────────────────────────────────────┘

  Claude Desktop                 MCP Server                WiFi Network
  ┌─────────────┐              ┌─────────────┐           ┌─────────────┐
  │             │              │  flipper-   │           │             │
  │   Claude    │─────stdio────│     mcp     │───WiFi────│   Router    │
  │             │              │   Server    │           │             │
  └─────────────┘              └─────────────┘           └──────┬──────┘
                                     │                          │
                                     │                          │
                              MCP Protocol              ┌───────▼──────┐
                              (JSON-RPC)                │ WiFi Dev     │
                                     │                  │ Board (ESP32)│
                                     │                  │ 192.168.1.100│
                                     │                  └──────┬───────┘
                                     │                         │
                                     ▼                         │ UART
                            ┌─────────────────┐                │
                            │  WiFiTransport  │                │
                            │                 │                │
                            │ - TCP Socket    │◄───────────────┘
                            │ - Host/Port     │
                            └────────┬────────┘
                                     │
                                     ▼
                            ┌─────────────────┐
                            │  ProtobufRPC    │
                            │                 │
                            │ - Framing       │
                            │ - Encode/Decode │
                            └────────┬────────┘
                                     │
                                     ▼
                            ┌─────────────────┐         ┌─────────────┐
                            │ FlipperClient   │         │ Flipper Zero│
                            │                 │◄───RPC──│   Device    │
                            │ - storage       │         │             │
                            │ - app           │         │  SD Card:   │
                            └────────┬────────┘         │  /ext/      │
                                     │                  └─────────────┘
                                     ▼
                            ┌─────────────────┐
                            │  MusicModule    │
                            │                 │
                            │ - FMF Format    │
                            │ - Validation    │
                            └─────────────────┘
```

### Step-by-Step: Playing a Song Over WiFi

Let's walk through creating and playing "Happy Birthday" on the Flipper Zero:

#### Step 1: Environment Setup

```bash
# Configure WiFi transport
export FLIPPER_TRANSPORT=wifi
export FLIPPER_WIFI_HOST=192.168.1.100  # Your WiFi Dev Board IP
export FLIPPER_WIFI_PORT=8080

# Enable debug logging (optional)
export FLIPPER_DEBUG=1

# Start the MCP server
flipper-mcp
```

#### Step 2: MCP Server Initialization

```
[MCP Server Startup Sequence]

1. Load configuration from environment
   ├─ FLIPPER_TRANSPORT=wifi
   ├─ FLIPPER_WIFI_HOST=192.168.1.100
   └─ FLIPPER_WIFI_PORT=8080

2. Initialize WiFi Transport
   ├─ Create TCP socket
   └─ Set connection parameters

3. Discover and load modules
   ├─ systeminfo ✓
   ├─ badusb ✓
   └─ music ✓

4. Register MCP tools
   └─ music_play, music_get_format

5. Ready - waiting for MCP client connection (stdio)
```

#### Step 3: Client Connects to MCP Server

```json
// Claude Desktop → MCP Server (stdio)
{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "params": {}
}

// MCP Server → Claude Desktop
{
  "jsonrpc": "2.0",
  "result": {
    "tools": [
      {
        "name": "music_play",
        "description": "Play a song on the Flipper Zero piezo speaker...",
        "inputSchema": { ... }
      },
      // ... other tools
    ]
  }
}
```

#### Step 4: User Requests Song Playback

User (via Claude): "Please play Happy Birthday on my Flipper Zero"

Claude decides to call the `music_play` tool:

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "music_play",
    "arguments": {
      "song_data": "Filetype: Flipper Music Format\nVersion: 0\nBPM: 120\nDuration: 4\nOctave: 4\nNotes: 4C, 4C, 4D, 4C, 4F, 4E, 4C, 4C, 4D, 4C, 4G, 4F",
      "filename": "happy_birthday.fmf",
      "play_immediately": true
    }
  }
}
```

#### Step 5: MCP Server Processes Request

```
[MCP Server Execution Flow]

MCPServer.handle_tool_call()
  │
  ├─ Route to MusicModule
  │
  └─ MusicModule.handle_tool_call("music_play", args)
       │
       ├─ Validate FMF format
       │   └─ validate_fmf_format() ✓
       │
       ├─ Connect to Flipper (WiFi)
       │   │
       │   └─ WiFiTransport.connect()
       │       ├─ TCP connect to 192.168.1.100:8080
       │       ├─ ProtobufRPC.initialize()
       │       │   ├─ Send: b'start_rpc_session\r'
       │       │   └─ Enter RPC mode ✓
       │       │
       │       └─ Connected ✓
       │
       ├─ Create music directory
       │   └─ storage.mkdir("/ext/apps_data/music_player")
       │       │
       │       └─ [Protobuf RPC sequence...]
       │
       ├─ Write song file
       │   └─ storage.write("/ext/apps_data/music_player/happy_birthday.fmf", song_data)
       │       │
       │       └─ [Protobuf RPC sequence...]
       │
       └─ Return success ✓
```

#### Step 6: Detailed Protobuf RPC Exchange

Let's zoom into the **storage.write()** operation:

```
┌─────────────────────────────────────────────────────────────────────┐
│             Detailed RPC Sequence: Writing Song File                │
└─────────────────────────────────────────────────────────────────────┘

Python (MCP Server)         WiFi (Network)          ESP32            Flipper
     │                           │                    │                 │
     │ storage.write()           │                    │                 │
     │      ↓                    │                    │                 │
     │ Build protobuf msg        │                    │                 │
     │ Main {                    │                    │                 │
     │   command_id: 5           │                    │                 │
     │   storage_write_request { │                    │                 │
     │     path: "/ext/..."      │                    │                 │
     │     file {                │                    │                 │
     │       data: "Filetype..." │                    │                 │
     │     }                     │                    │                 │
     │   }                       │                    │                 │
     │ }                         │                    │                 │
     │      ↓                    │                    │                 │
     │ Serialize to bytes        │                    │                 │
     │      ↓                    │                    │                 │
     │ Add varint framing        │                    │                 │
     │ [0x4A][0x08,0x12...]      │                    │                 │
     │      ↓                    │                    │                 │
     ├──TCP send──────────────►  │                    │                 │
     │                           ├──WiFi packet──────►│                 │
     │                           │                    │                 │
     │                           │                    │ TCP recv        │
     │                           │                    │     ↓           │
     │                           │                    │ Forward UART    │
     │                           │                    ├────────────────►│
     │                           │                    │                 │
     │                           │                    │              RPC│
     │                           │                    │           Handler│
     │                           │                    │              │  │
     │                           │                    │              ▼  │
     │                           │                    │         Write to│
     │                           │                    │         SD Card │
     │                           │                    │              │  │
     │                           │                    │              ▼  │
     │                           │                    │         Response│
     │                           │                    │ ◄───────────┘  │
     │                           │                    │                 │
     │                           │                    │ Main {          │
     │                           │                    │   command_id: 5 │
     │                           │                    │   status: OK    │
     │                           │                    │ }               │
     │                           │                    │                 │
     │                           │                    │ ◄───UART────────┤
     │                           │                    │                 │
     │                           │ ◄──WiFi packet─────┤                 │
     │ ◄──TCP recv─────────────┤  │                    │                 │
     │      ↓                    │                    │                 │
     │ Read varint               │                    │                 │
     │      ↓                    │                    │                 │
     │ Read message bytes        │                    │                 │
     │      ↓                    │                    │                 │
     │ Parse protobuf            │                    │                 │
     │      ↓                    │                    │                 │
     │ Return success ✓          │                    │                 │
     │                           │                    │                 │
```

#### Step 7: Data on the Wire

Here's what the actual network traffic looks like:

**TCP Packet (WiFi → ESP32): Storage Write Request**
```
# Ethernet Frame
Destination MAC: aa:bb:cc:dd:ee:ff  (ESP32 WiFi MAC)
Source MAC: 11:22:33:44:55:66       (Computer WiFi MAC)

# IP Packet  
Source IP: 192.168.1.50              (Computer)
Dest IP: 192.168.1.100               (WiFi Dev Board)

# TCP Segment
Source Port: 51234                   (Random client port)
Dest Port: 8080                      (WiFi Dev Board listening port)
Flags: PSH, ACK
Sequence: 1000

# Payload (Protobuf RPC - Hex dump)
4A 08 12 2F 2F 65 78 74 2F 61 70 70 73 5F 64 61  J../ext/apps_da
74 61 2F 6D 75 73 69 63 5F 70 6C 61 79 65 72 2F  ta/music_player/
68 61 70 70 79 5F 62 69 72 74 68 64 61 79 2E 66  happy_birthday.f
6D 66 1A 46 69 6C 65 74 79 70 65 3A 20 46 6C 69  mf.Filetype: Fli
70 70 65 72 20 4D 75 73 69 63 20 46 6F 72 6D 61  pper Music Forma
74 0A 56 65 72 73 69 6F 6E 3A 20 30 0A ...       t.Version: 0....

# Decoded:
# [Varint: 0x4A = 74 bytes follow]
# [Protobuf Main message containing StorageWriteRequest]
```

**UART (ESP32 → Flipper): Same Data**
```
# Serial UART @ 115200 baud
# Exact same bytes are forwarded:
4A 08 12 2F 2F 65 78 74 2F 61 70 70 73 5F 64 61
74 61 2F 6D 75 73 69 63 5F 70 6C 61 79 65 72 2F
... (same as TCP payload)
```

#### Step 8: File Created on Flipper Zero

```
Flipper Zero SD Card Filesystem:
/ext/
├── apps/
├── apps_data/
│   ├── badusb/
│   └── music_player/
│       ├── happy_birthday.fmf  ← NEW FILE
│       └── Marble_Machine.fmf
└── ...
```

**File Contents** (`/ext/apps_data/music_player/happy_birthday.fmf`):
```
Filetype: Flipper Music Format
Version: 0
BPM: 120
Duration: 4
Octave: 4
Notes: 4C, 4C, 4D, 4C, 4F, 4E, 4C, 4C, 4D, 4C, 4G, 4F
```

#### Step 9: MCP Server Returns Result

```json
// MCP Server → Claude Desktop
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "✅ Song saved: happy_birthday.fmf\n\n📁 Path: /ext/apps_data/music_player/happy_birthday.fmf\n📊 Size: 87 characters\n\n🎵 Saved. Please open the Music Player app on your Flipper Zero and select the file to play.\n\n📄 Song data (saved, normalized):\n```fmf\nFiletype: Flipper Music Format\nVersion: 0\nBPM: 120\nDuration: 4\nOctave: 4\nNotes: 4C, 4C, 4D, 4C, 4F, 4E, 4C, 4C, 4D, 4C, 4G, 4F\n```"
      }
    ]
  }
}
```

Claude responds to user: "I've successfully created and saved the 'Happy Birthday' song to your Flipper Zero! The file is saved at `/ext/apps_data/music_player/happy_birthday.fmf`. To play it, please open the Music Player app on your Flipper Zero and select the file."

### Song Lifecycle Summary

```
┌────────────────────────────────────────────────────────────────┐
│                    Song Lifecycle States                       │
└────────────────────────────────────────────────────────────────┘

1. [CREATED]      User requests song via Claude
                      ↓
2. [FORMATTED]    MusicModule formats in FMF v0
                      ↓
3. [VALIDATED]    FMF format validation passes
                      ↓
4. [TRANSMITTED]  Song data sent over WiFi → UART
                      ↓
5. [STORED]       File written to SD card
                      ↓
6. [AVAILABLE]    Music Player app can see file
                      ↓
7. [PLAYING]      User opens Music Player → selects file → plays
```

### Performance Metrics

Typical timings for WiFi operations:

- **Connection**: 50-200ms (TCP handshake + RPC init)
- **Small file write** (< 1KB): 100-300ms
- **Large file write** (10KB): 500-1500ms
- **Directory listing**: 50-150ms
- **Ping (round-trip)**: 10-50ms

**Note**: Timings depend on WiFi signal strength, network congestion, and SD card speed.

---

## Implementation Guide

### Setting Up the MCP Server for WiFi

#### Installation

```bash
# Clone repository
git clone https://github.com/busse/flipperzero-mcp.git
cd flipperzero-mcp

# Install in development mode
pip install -e .
```

#### Configuration for WiFi

```bash
# Create configuration script
cat > flipper-wifi.sh << 'EOF'
#!/bin/bash

# WiFi configuration
export FLIPPER_TRANSPORT=wifi
export FLIPPER_WIFI_HOST=192.168.1.100  # Your WiFi Dev Board IP
export FLIPPER_WIFI_PORT=8080

# Optional: Enable debug logging
export FLIPPER_DEBUG=1

# Start server
flipper-mcp
EOF

chmod +x flipper-wifi.sh

# Run
./flipper-wifi.sh
```

#### Python Client Example

```python
#!/usr/bin/env python3
"""Example: Using Music Player module over WiFi."""

import asyncio
import sys
from pathlib import Path

# Add src to path if running from repo
sys.path.insert(0, str(Path(__file__).parent / "src"))

from flipper_mcp.modules.music import MusicModule
from flipper_mcp.core.flipper_client import FlipperClient
from flipper_mcp.core.transport.wifi import WiFiTransport


async def play_song_over_wifi():
    """Play a song on Flipper Zero over WiFi."""
    
    # Step 1: Configure WiFi transport
    config = {
        "host": "192.168.1.100",  # WiFi Dev Board IP
        "port": 8080,
        "connect_timeout": 3.0,
    }
    
    # Step 2: Create transport and client
    transport = WiFiTransport(config)
    client = FlipperClient(transport)
    
    # Step 3: Connect
    print("Connecting to Flipper Zero over WiFi...")
    connected = await client.connect()
    
    if not connected:
        print("❌ Failed to connect")
        return False
    
    print("✅ Connected!")
    
    # Step 4: Create music module
    music = MusicModule(client)
    
    # Step 5: Define song in FMF format
    song = """Filetype: Flipper Music Format
Version: 0
BPM: 140
Duration: 8
Octave: 5
Notes: E, E, E, E, E, E, E, G, C, D, E
"""
    
    # Step 6: Play song
    print("Playing song...")
    result = await music.handle_tool_call("music_play", {
        "song_data": song,
        "filename": "test_song.fmf",
        "play_immediately": True
    })
    
    # Step 7: Display result
    for content in result:
        print(content.text)
    
    # Step 8: Cleanup
    await client.disconnect()
    print("Disconnected")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(play_song_over_wifi())
    sys.exit(0 if success else 1)
```

### ESP32 Firmware Reference Implementation

While complete firmware source varies by implementation, here's a reference architecture:

```cpp
/**
 * ESP32 WiFi-UART Bridge Firmware
 * 
 * Bridges TCP WiFi connections to UART for Flipper Zero
 * Implements transparent byte forwarding to preserve protobuf framing
 */

#include <WiFi.h>
#include <HardwareSerial.h>

// Configuration
const char* WIFI_SSID = "YourNetwork";
const char* WIFI_PASSWORD = "YourPassword";
const int TCP_PORT = 8080;
const int UART_BAUD = 115200;
const int UART_RX_PIN = 16;
const int UART_TX_PIN = 17;

// Globals
WiFiServer server(TCP_PORT);
WiFiClient client;
HardwareSerial flipperSerial(1);  // Use UART1

void setup() {
  // Initialize serial for debugging
  Serial.begin(115200);
  Serial.println("Flipper WiFi Bridge Starting...");
  
  // Initialize UART to Flipper
  flipperSerial.begin(UART_BAUD, SERIAL_8N1, UART_RX_PIN, UART_TX_PIN);
  
  // Connect to WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println();
  Serial.print("Connected! IP: ");
  Serial.println(WiFi.localIP());
  
  // Start TCP server
  server.begin();
  Serial.println("TCP Server started on port " + String(TCP_PORT));
}

void loop() {
  // Accept new connections
  if (!client.connected()) {
    client = server.available();
    if (client) {
      Serial.println("Client connected: " + client.remoteIP().toString());
    }
  }
  
  if (client.connected()) {
    // Forward TCP → UART (WiFi to Flipper)
    while (client.available()) {
      uint8_t byte = client.read();
      flipperSerial.write(byte);
    }
    
    // Forward UART → TCP (Flipper to WiFi)
    while (flipperSerial.available()) {
      uint8_t byte = flipperSerial.read();
      client.write(byte);
    }
  }
  
  // Small delay to prevent watchdog issues
  delay(1);
}
```

**Key Points**:
- **Transparent forwarding**: Bytes are forwarded without interpretation
- **Bidirectional**: Both directions are handled independently
- **No buffering**: Immediate forwarding preserves timing and framing
- **Simple**: No complex logic reduces bugs

---

## Code Patterns

### Pattern 1: WiFi Transport Usage

```python
from flipper_mcp.core.transport.wifi import WiFiTransport
from flipper_mcp.core.flipper_client import FlipperClient

# Configure
config = {
    "host": "192.168.1.100",
    "port": 8080,
    "connect_timeout": 3.0,
    "read_chunk_size": 4096,
}

# Create and connect
transport = WiFiTransport(config)
client = FlipperClient(transport)

connected = await client.connect()
if not connected:
    raise ConnectionError("Failed to connect to Flipper Zero")

# Use client...
info = await client.rpc.system_device_info()
print(f"Device: {info}")

# Disconnect
await client.disconnect()
```

### Pattern 2: Robust Connection with Retry

```python
import asyncio

async def connect_with_retry(host: str, port: int, max_retries: int = 3):
    """Connect to Flipper with retry logic."""
    for attempt in range(max_retries):
        try:
            transport = WiFiTransport({"host": host, "port": port})
            client = FlipperClient(transport)
            
            if await client.connect():
                print(f"✅ Connected on attempt {attempt + 1}")
                return client
            
        except Exception as e:
            print(f"❌ Attempt {attempt + 1} failed: {e}")
        
        if attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    raise ConnectionError("All connection attempts failed")
```

### Pattern 3: Storage Operations

```python
async def manage_files(client: FlipperClient):
    """Example storage operations over WiFi."""
    
    # List directory
    files = await client.storage.list("/ext/apps_data/music_player")
    print(f"Files: {files}")
    
    # Read file
    content = await client.storage.read("/ext/apps_data/music_player/song.fmf")
    print(f"Content: {content}")
    
    # Write file
    new_song = "Filetype: Flipper Music Format\n..."
    success = await client.storage.write("/ext/apps_data/music_player/new.fmf", new_song)
    print(f"Write: {'✅' if success else '❌'}")
    
    # Delete file
    deleted = await client.storage.delete("/ext/apps_data/music_player/old.fmf")
    print(f"Delete: {'✅' if deleted else '❌'}")
```

### Pattern 4: Error Handling

```python
async def safe_operation(client: FlipperClient):
    """Proper error handling for WiFi operations."""
    try:
        # Check connection first
        if not await client.transport.is_connected():
            print("Not connected - attempting reconnect...")
            await client.connect()
        
        # Perform operation with timeout
        result = await asyncio.wait_for(
            client.rpc.system_ping(),
            timeout=5.0
        )
        
        return result
        
    except asyncio.TimeoutError:
        print("❌ Operation timed out - WiFi may be unstable")
        return None
        
    except ConnectionError as e:
        print(f"❌ Connection lost: {e}")
        # Attempt reconnect
        await client.connect()
        return None
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None
```

### Pattern 5: Module Integration

```python
from flipper_mcp.modules.music import MusicModule

async def use_module_over_wifi():
    """Use any module over WiFi - they work transparently."""
    
    # Setup (WiFi transport)
    config = {"host": "192.168.1.100", "port": 8080}
    transport = WiFiTransport(config)
    client = FlipperClient(transport)
    await client.connect()
    
    # Create module - no knowledge of transport type
    music = MusicModule(client)
    
    # Use module - works identically whether WiFi or USB
    result = await music.handle_tool_call("music_play", {
        "song_data": "Filetype: Flipper Music Format\n...",
        "filename": "test.fmf",
        "play_immediately": True
    })
    
    print(result[0].text)
```

---

## Troubleshooting

### Connection Issues

#### Problem: Cannot connect to WiFi Dev Board

```
Error: WiFi connection failed: [Errno 111] Connection refused
```

**Solutions**:

1. **Verify IP address**:
   ```bash
   # Find ESP32 on network
   nmap -sn 192.168.1.0/24
   # Or check router DHCP leases
   ```

2. **Check port**:
   ```bash
   nc -zv 192.168.1.100 8080
   ```

3. **Verify firmware is running**:
   - Check ESP32 serial debug output
   - Look for "TCP Server started" message

4. **Check firewall**:
   ```bash
   # Temporarily disable firewall for testing
   sudo ufw disable  # Ubuntu
   ```

#### Problem: Connection drops frequently

**Solutions**:

1. **Improve WiFi signal**: Move closer to router or use 5GHz band
2. **Increase timeouts**:
   ```python
   config = {
       "host": "192.168.1.100",
       "port": 8080,
       "connect_timeout": 5.0,  # Increase from 3.0
   }
   ```
3. **Check ESP32 power supply**: Ensure stable 3.3V power
4. **Update ESP32 WiFi library**: Older libraries have stability issues

### RPC Issues

#### Problem: RPC commands timeout

```
Error: Timeout waiting for RPC response
```

**Solutions**:

1. **Verify RPC session started**:
   ```python
   # Enable debug logging
   export FLIPPER_DEBUG=1
   
   # Look for "Entering RPC mode" in logs
   ```

2. **Force RPC session start**:
   ```bash
   export FLIPPER_FORCE_START_RPC_SESSION=1
   ```

3. **Check UART connection**: Verify TX/RX are not swapped

#### Problem: Corrupted protobuf messages

```
Error: Failed to parse protobuf message
```

**Solutions**:

1. **Verify baud rate matches**: ESP32 and Flipper must use same rate (115200)
2. **Check for electrical noise**: Add pull-up resistors on UART lines
3. **Verify framing preservation**: ESP32 firmware must not buffer varints

### Storage Issues

#### Problem: Cannot write files

```
Error: Failed to write song file
```

**Solutions**:

1. **Verify SD card is inserted**:
   ```python
   sd_available = await client.check_sd_card_available()
   print(f"SD Card: {sd_available}")
   ```

2. **Check free space**:
   - Flipper UI → Settings → Storage Info

3. **Verify directory exists**:
   ```python
   await client.storage.mkdir("/ext/apps_data/music_player")
   ```

4. **Check permissions**: SD card should be formatted as FAT32

### Debug Tools

#### Enable Verbose Logging

```bash
# Maximum verbosity
export FLIPPER_DEBUG=1
export FLIPPER_FORCE_START_RPC_SESSION=1

flipper-mcp
```

#### Network Packet Capture

```bash
# Capture WiFi traffic
sudo tcpdump -i wlan0 -w flipper-wifi.pcap host 192.168.1.100

# Analyze in Wireshark
wireshark flipper-wifi.pcap
```

#### Serial Monitor (ESP32)

```bash
# Monitor ESP32 debug output
screen /dev/ttyUSB0 115200
# or
minicom -D /dev/ttyUSB0 -b 115200
```

#### Test Connection Manually

```python
#!/usr/bin/env python3
"""Manual connection test."""
import asyncio

async def test():
    # Connect to ESP32
    reader, writer = await asyncio.open_connection('192.168.1.100', 8080)
    print("✅ Connected")
    
    # Send RPC session start
    writer.write(b'start_rpc_session\r')
    await writer.drain()
    print("✅ Sent RPC start")
    
    # Wait for response
    await asyncio.sleep(0.5)
    try:
        data = await asyncio.wait_for(reader.read(1024), timeout=1.0)
        print(f"✅ Received: {data}")
    except asyncio.TimeoutError:
        print("⚠️  No response (may be normal)")
    
    writer.close()
    await writer.wait_closed()

asyncio.run(test())
```

---

## References

### Official Flipper Zero Resources

- **Flipper Zero Official Site**: [flipperzero.one](https://flipperzero.one/)
- **Firmware Repository**: [github.com/flipperdevices/flipperzero-firmware](https://github.com/flipperdevices/flipperzero-firmware)
- **Protobuf Definitions**: [github.com/flipperdevices/flipperzero-protobuf](https://github.com/flipperdevices/flipperzero-protobuf)
- **Official Documentation**: [docs.flipperzero.one](https://docs.flipperzero.one/)
- **Developer Docs**: [developer.flipper.net](https://developer.flipper.net/)

### WiFi Dev Board Resources

- **ESP32 Official**: [espressif.com/en/products/socs/esp32](https://www.espressif.com/en/products/socs/esp32)
- **ESP-IDF Documentation**: [docs.espressif.com/projects/esp-idf](https://docs.espressif.com/projects/esp-idf/en/latest/)
- **Arduino ESP32**: [github.com/espressif/arduino-esp32](https://github.com/espressif/arduino-esp32)

### Protocol Buffers

- **Protocol Buffers**: [protobuf.dev](https://protobuf.dev/)
- **Nanopb (Embedded)**: [github.com/nanopb/nanopb](https://github.com/nanopb/nanopb)
- **Python Protobuf**: [pypi.org/project/protobuf](https://pypi.org/project/protobuf/)

### Model Context Protocol (MCP)

- **MCP Specification**: [modelcontextprotocol.io](https://modelcontextprotocol.io/)
- **MCP Python SDK**: [github.com/modelcontextprotocol/python-sdk](https://github.com/modelcontextprotocol/python-sdk)

### This Project

- **Repository**: [github.com/busse/flipperzero-mcp](https://github.com/busse/flipperzero-mcp)
- **Documentation**: [docs/](../docs/)
- **Issues**: [github.com/busse/flipperzero-mcp/issues](https://github.com/busse/flipperzero-mcp/issues)

### Community

- **Flipper Zero Forum**: [forum.flipperzero.one](https://forum.flipperzero.one/)
- **Flipper Zero Discord**: [discord.gg/flipperzero](https://discord.gg/flipperzero)
- **Reddit**: [r/flipperzero](https://www.reddit.com/r/flipperzero/)

---

## Appendix: FMF Format Quick Reference

```
Filetype: Flipper Music Format
Version: 0
BPM: <60-240>          # Beats per minute
Duration: <1|2|4|8|16> # Default note duration
Octave: <3-7>          # Default octave
Notes: <note_list>     # Comma-separated notes

Note Format:
  [duration]<note>[accidental][octave][dot]
  
Examples:
  C      # C in default octave/duration
  4C     # Quarter note C
  C#5    # C sharp in octave 5
  8A#4   # Eighth note A sharp in octave 4
  P      # Pause/rest
  4P     # Quarter note rest
```

---

**Document Version**: 1.0  
**Last Updated**: 2025-12-28  
**Author**: Flipper Zero MCP Project  
**License**: MIT
