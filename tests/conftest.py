"""Shared pytest fixtures for flipper-mcp tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock


def make_mock_pb2_file(name="test.txt", ftype="FILE", size=42):
    """Build a mock protobuf-style file entry dict."""
    return {"name": name, "type": ftype, "size": size}


@pytest.fixture
def mock_protobuf_rpc():
    """Mock of ProtobufRPC with all async methods pre-wired."""
    pb = MagicMock()

    # Storage
    pb.storage_list_detailed = AsyncMock(return_value=[
        {"name": "file.txt", "type": "FILE", "size": 128},
        {"name": "subdir",   "type": "DIR",  "size": 0},
    ])
    pb.storage_read   = AsyncMock(return_value=b"hello world")
    pb.storage_write  = AsyncMock(return_value=True)
    pb.storage_mkdir  = AsyncMock(return_value=True)
    pb.storage_delete = AsyncMock(return_value=True)
    pb.storage_rename = AsyncMock(return_value=True)
    pb.storage_stat   = AsyncMock(return_value={"name": "file.txt", "type": "FILE", "size": 128})
    pb.storage_md5sum = AsyncMock(return_value="d8e8fca2dc0f896fd7cb4cb0031ba249")
    pb.storage_info   = AsyncMock(return_value=(1_000_000, 750_000))

    # App
    pb.app_start          = AsyncMock(return_value=True)
    pb.app_exit           = AsyncMock(return_value=True)
    pb.app_load_file      = AsyncMock(return_value=True)
    pb.app_lock_status    = AsyncMock(return_value=False)
    pb.app_get_error      = AsyncMock(return_value={"code": 0, "text": ""})
    pb.app_button_press   = AsyncMock(return_value=True)
    pb.app_button_release = AsyncMock(return_value=True)
    pb.app_data_exchange  = AsyncMock(return_value=True)

    # GUI
    pb.gui_capture_screen_frame = AsyncMock(return_value={
        "data": bytes(1024),  # all-zero frame
        "orientation": 0,
    })
    pb.gui_send_input_event = AsyncMock(return_value=True)

    return pb


@pytest.fixture
def mock_flipper(mock_protobuf_rpc):
    """Mock FlipperClient with rpc.protobuf_rpc wired."""
    rpc = MagicMock()
    rpc.protobuf_rpc = mock_protobuf_rpc

    client = MagicMock()
    client.rpc = rpc
    return client
