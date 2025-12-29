# `core.transport`

Transports implement the byte-oriented connection to the Flipper device.

## Implementations

- `AutoTransport`: selects a transport at runtime (USB-first, WiFi fallback when configured)
- `USBTransport`: serial over USB CDC (auto-detects Flipper VID:PID when possible)
- `WiFiTransport`: TCP socket transport (host/port are configured via the server config dict)
- `BluetoothTransport`: stub transport (not implemented)

## Framing support

`FlipperTransport` provides:

- `receive_exact(n, timeout)` for framed protocols (like protobuf delimited framing)
- a receive buffer (`_rx_buffer`) and `clear_receive_buffer()`



