# Protobuf RPC Implementation

## Overview

This document describes the implementation of Flipper Zero RPC protocol using Protocol Buffers, based on the official schemas from [flipperzero-protobuf](https://github.com/flipperdevices/flipperzero-protobuf).

## Current Implementation

### Files Created

1. **`src/flipper_mcp/core/protobuf_rpc.py`**
   - Manual protobuf encoding/decoding implementation
   - Handles `DeviceInfoRequest`/`DeviceInfoResponse`
   - Handles `Property.GetRequest`/`Property.GetResponse`
   - Implements the `Main` message wrapper protocol

2. **`proto/` directory**
   - Contains downloaded `.proto` schema files:
     - `system.proto` - System RPC methods
     - `property.proto` - Property RPC methods
     - `flipper.proto` - Main message wrapper
     - `storage.proto` - Storage RPC methods

### Integration

The protobuf RPC is integrated into the existing `FlipperRPC` class:
- Tries protobuf RPC first (if available)
- Falls back to simplified RPC methods
- Falls back to CLI tools if available
- Final fallback to basic info

## Protocol Structure

The Flipper Zero RPC protocol uses:

1. **Message Framing**: 4-byte length prefix (big-endian)
2. **Main Message Wrapper**:
   ```protobuf
   message Main {
       uint32 command_id = 1;
       CommandStatus command_status = 2;
       bool has_next = 3;
       oneof content {
           ... request/response messages ...
       }
   }
   ```

3. **DeviceInfo Response**: Returns key-value pairs (multiple responses with `has_next` flag)

## Next Steps for Full Implementation

### Option 1: Use Official Python Library (Recommended)

Install the official Python protobuf library:
```bash
pip install flipperzero-protobuf-py
# Or from source:
# git clone https://github.com/flipperdevices/flipperzero_protobuf_py
# cd flipperzero_protobuf_py
# pip install -e .
```

Then update `protobuf_rpc.py` to use the generated protobuf classes.

### Option 2: Generate Python Code from .proto Files

1. Install Protocol Buffers compiler:
   ```bash
   # macOS
   brew install protobuf
   
   # Linux
   sudo apt-get install protobuf-compiler
   ```

2. Generate Python code:
   ```bash
   cd proto
   protoc --python_out=../src/flipper_mcp/core/protobuf_gen \
          --proto_path=. \
          system.proto property.proto flipper.proto storage.proto
   ```

3. Update `protobuf_rpc.py` to import and use the generated classes.

### Option 3: Debug Current Implementation

The current manual implementation may need debugging:
- Verify protobuf message encoding/decoding
- Check message framing format
- Handle `has_next` flag for multiple DeviceInfo responses
- Test with actual device responses

## Testing

To test the implementation:

```bash
python3 test_systeminfo.py
```

The output should show real device information once the protobuf RPC is working correctly.

## References

- [Flipper Zero Protobuf Repository](https://github.com/flipperdevices/flipperzero-protobuf)
- [Flipper Zero Protobuf Python Library](https://github.com/flipperdevices/flipperzero_protobuf_py)
- [Flipper Zero RPC Documentation](https://docs.flipper.net/)

