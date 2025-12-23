import os
from pathlib import Path

import pytest

from flipper_mcp.core.transport.usb import USBTransport
from flipper_mcp.core.protobuf_rpc import ProtobufRPC


def _get_port() -> str:
    return os.environ.get("FLIPPER_PORT", "/dev/cu.usbmodemflip_Luec1ni1")


def _port_exists(port: str) -> bool:
    return Path(port).exists()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_protobuf_ping_device_info_property():
    """
    Hardware-gated smoke test.

    Requires a connected Flipper Zero on FLIPPER_PORT (defaults to the user-provided
    /dev/cu.usbmodemflip_Luec1ni1).
    """
    port = _get_port()
    if not _port_exists(port):
        pytest.skip(f"Flipper port not found: {port} (set FLIPPER_PORT)")

    transport = USBTransport({"port": port, "baudrate": 115200, "timeout": 1.0})
    if not await transport.connect():
        pytest.skip(f"Could not connect to Flipper on {port}")

    try:
        rpc = ProtobufRPC(transport)

        # Ping
        echoed = await rpc.ping(b"mcp")
        assert echoed is not None

        # Device info
        info = await rpc.get_device_info()
        assert isinstance(info, dict)
        # We can't guarantee exact keys across firmwares, but we should get at least one kv pair.
        assert len(info) > 0

        # Property get (best effort; assert it doesn't crash and returns str/None)
        fw = await rpc.get_property("firmware_version")
        assert fw is None or isinstance(fw, str)

        # Storage list (root should always contain ext/int mount points)
        root = await rpc.storage_list("/")
        assert isinstance(root, list)
        assert "ext" in root
    finally:
        await transport.disconnect()


