"""Tests for the Storage module."""

import base64
import pytest
from unittest.mock import AsyncMock, MagicMock

from flipper_mcp.modules.storage.module import StorageModule


# ── Helpers ───────────────────────────────────────────────────────────────────

def _no_rpc_client():
    """Flipper client with no RPC available."""
    client = MagicMock()
    client.rpc = None
    return client


# ── Module meta ───────────────────────────────────────────────────────────────

def test_storage_module_properties(mock_flipper):
    m = StorageModule(mock_flipper)
    assert m.name == "storage"
    assert m.version == "1.0.0"
    assert "storage" in m.description.lower()


def test_storage_tools(mock_flipper):
    tools = StorageModule(mock_flipper).get_tools()
    names = [t.name for t in tools]
    assert len(tools) == 9
    for expected in [
        "storage_list", "storage_read", "storage_write",
        "storage_mkdir", "storage_delete", "storage_rename",
        "storage_stat", "storage_md5", "storage_info",
    ]:
        assert expected in names


# ── storage_list ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_storage_list_success(mock_flipper):
    m = StorageModule(mock_flipper)
    result = await m.handle_tool_call("storage_list", {"path": "/ext"})

    assert len(result) == 1
    text = result[0].text
    assert "file.txt" in text
    assert "subdir" in text
    assert "FILE" in text
    assert "DIR" in text
    assert "2 entries" in text


@pytest.mark.asyncio
async def test_storage_list_empty(mock_flipper, mock_protobuf_rpc):
    mock_protobuf_rpc.storage_list_detailed = AsyncMock(return_value=[])
    m = StorageModule(mock_flipper)
    result = await m.handle_tool_call("storage_list", {"path": "/ext/empty"})

    assert "empty" in result[0].text.lower() or "does not exist" in result[0].text.lower()


@pytest.mark.asyncio
async def test_storage_list_no_rpc():
    m = StorageModule(_no_rpc_client())
    result = await m.handle_tool_call("storage_list", {"path": "/ext"})
    assert "not connected" in result[0].text.lower() or "unavailable" in result[0].text.lower()


@pytest.mark.asyncio
async def test_storage_list_calls_rpc_with_correct_path(mock_flipper, mock_protobuf_rpc):
    m = StorageModule(mock_flipper)
    await m.handle_tool_call("storage_list", {"path": "/int/apps"})
    mock_protobuf_rpc.storage_list_detailed.assert_awaited_once_with("/int/apps", include_md5=False)


@pytest.mark.asyncio
async def test_storage_list_include_md5(mock_flipper, mock_protobuf_rpc):
    m = StorageModule(mock_flipper)
    await m.handle_tool_call("storage_list", {"path": "/ext", "include_md5": True})
    mock_protobuf_rpc.storage_list_detailed.assert_awaited_once_with("/ext", include_md5=True)


# ── storage_read ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_storage_read_text(mock_flipper):
    m = StorageModule(mock_flipper)
    result = await m.handle_tool_call("storage_read", {"path": "/ext/test.txt"})

    assert "hello world" in result[0].text


@pytest.mark.asyncio
async def test_storage_read_binary_auto(mock_flipper, mock_protobuf_rpc):
    """Binary content falls back to base64 in 'auto' mode."""
    mock_protobuf_rpc.storage_read = AsyncMock(return_value=b"\x00\xff\xfe\xfd")
    m = StorageModule(mock_flipper)
    result = await m.handle_tool_call("storage_read", {"path": "/ext/bin.bin"})

    assert "base64" in result[0].text.lower()
    b64_part = result[0].text.split("\n\n", 1)[1].strip()
    assert base64.b64decode(b64_part) == b"\x00\xff\xfe\xfd"


@pytest.mark.asyncio
async def test_storage_read_force_base64(mock_flipper):
    m = StorageModule(mock_flipper)
    result = await m.handle_tool_call("storage_read", {"path": "/ext/test.txt", "encoding": "base64"})

    assert "base64" in result[0].text.lower()
    b64_part = result[0].text.split("\n\n", 1)[1].strip()
    assert base64.b64decode(b64_part) == b"hello world"


@pytest.mark.asyncio
async def test_storage_read_empty_file(mock_flipper, mock_protobuf_rpc):
    mock_protobuf_rpc.storage_read = AsyncMock(return_value=b"")
    m = StorageModule(mock_flipper)
    result = await m.handle_tool_call("storage_read", {"path": "/ext/empty.txt"})

    assert "empty" in result[0].text.lower() or "does not exist" in result[0].text.lower()


@pytest.mark.asyncio
async def test_storage_read_no_rpc():
    m = StorageModule(_no_rpc_client())
    result = await m.handle_tool_call("storage_read", {"path": "/ext/test.txt"})
    assert "unavailable" in result[0].text.lower() or "not connected" in result[0].text.lower()


# ── storage_write ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_storage_write_utf8(mock_flipper, mock_protobuf_rpc):
    m = StorageModule(mock_flipper)
    result = await m.handle_tool_call("storage_write", {
        "path": "/ext/out.txt",
        "content": "test data",
    })

    assert "9" in result[0].text  # len("test data") = 9 bytes
    mock_protobuf_rpc.storage_write.assert_awaited_once_with("/ext/out.txt", b"test data")


@pytest.mark.asyncio
async def test_storage_write_base64(mock_flipper, mock_protobuf_rpc):
    payload = b"\xde\xad\xbe\xef"
    m = StorageModule(mock_flipper)
    result = await m.handle_tool_call("storage_write", {
        "path": "/ext/bin.bin",
        "content": base64.b64encode(payload).decode(),
        "encoding": "base64",
    })

    assert "4" in result[0].text
    mock_protobuf_rpc.storage_write.assert_awaited_once_with("/ext/bin.bin", payload)


@pytest.mark.asyncio
async def test_storage_write_failure(mock_flipper, mock_protobuf_rpc):
    mock_protobuf_rpc.storage_write = AsyncMock(return_value=False)
    m = StorageModule(mock_flipper)
    result = await m.handle_tool_call("storage_write", {"path": "/ext/x.txt", "content": "x"})

    assert "failed" in result[0].text.lower()


# ── storage_mkdir / delete / rename ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_storage_mkdir_success(mock_flipper, mock_protobuf_rpc):
    m = StorageModule(mock_flipper)
    result = await m.handle_tool_call("storage_mkdir", {"path": "/ext/newdir"})
    assert "created" in result[0].text.lower()
    mock_protobuf_rpc.storage_mkdir.assert_awaited_once_with("/ext/newdir")


@pytest.mark.asyncio
async def test_storage_mkdir_failure(mock_flipper, mock_protobuf_rpc):
    mock_protobuf_rpc.storage_mkdir = AsyncMock(return_value=False)
    m = StorageModule(mock_flipper)
    result = await m.handle_tool_call("storage_mkdir", {"path": "/ext/fail"})
    assert "failed" in result[0].text.lower()


@pytest.mark.asyncio
async def test_storage_delete_success(mock_flipper, mock_protobuf_rpc):
    m = StorageModule(mock_flipper)
    result = await m.handle_tool_call("storage_delete", {"path": "/ext/old.txt"})
    assert "deleted" in result[0].text.lower()
    mock_protobuf_rpc.storage_delete.assert_awaited_once_with("/ext/old.txt", recursive=False)


@pytest.mark.asyncio
async def test_storage_delete_recursive(mock_flipper, mock_protobuf_rpc):
    m = StorageModule(mock_flipper)
    await m.handle_tool_call("storage_delete", {"path": "/ext/dir", "recursive": True})
    mock_protobuf_rpc.storage_delete.assert_awaited_once_with("/ext/dir", recursive=True)


@pytest.mark.asyncio
async def test_storage_rename_success(mock_flipper, mock_protobuf_rpc):
    m = StorageModule(mock_flipper)
    result = await m.handle_tool_call("storage_rename", {
        "old_path": "/ext/a.txt",
        "new_path": "/ext/b.txt",
    })
    assert "renamed" in result[0].text.lower()
    assert "/ext/a.txt" in result[0].text
    assert "/ext/b.txt" in result[0].text
    mock_protobuf_rpc.storage_rename.assert_awaited_once_with("/ext/a.txt", "/ext/b.txt")


@pytest.mark.asyncio
async def test_storage_rename_failure(mock_flipper, mock_protobuf_rpc):
    mock_protobuf_rpc.storage_rename = AsyncMock(return_value=False)
    m = StorageModule(mock_flipper)
    result = await m.handle_tool_call("storage_rename", {
        "old_path": "/ext/a.txt", "new_path": "/ext/b.txt"
    })
    assert "failed" in result[0].text.lower()


# ── storage_stat ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_storage_stat_file(mock_flipper):
    m = StorageModule(mock_flipper)
    result = await m.handle_tool_call("storage_stat", {"path": "/ext/file.txt"})

    assert "FILE" in result[0].text
    assert "128" in result[0].text


@pytest.mark.asyncio
async def test_storage_stat_directory(mock_flipper, mock_protobuf_rpc):
    mock_protobuf_rpc.storage_stat = AsyncMock(return_value={"name": "apps", "type": "DIR", "size": 0})
    m = StorageModule(mock_flipper)
    result = await m.handle_tool_call("storage_stat", {"path": "/ext/apps"})

    assert "DIR" in result[0].text
    # Size should not be shown for directories
    assert "Size" not in result[0].text


@pytest.mark.asyncio
async def test_storage_stat_not_found(mock_flipper, mock_protobuf_rpc):
    mock_protobuf_rpc.storage_stat = AsyncMock(return_value=None)
    m = StorageModule(mock_flipper)
    result = await m.handle_tool_call("storage_stat", {"path": "/ext/missing.txt"})
    assert "not found" in result[0].text.lower()


# ── storage_md5 ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_storage_md5_success(mock_flipper):
    m = StorageModule(mock_flipper)
    result = await m.handle_tool_call("storage_md5", {"path": "/ext/file.txt"})

    assert "d8e8fca2dc0f896fd7cb4cb0031ba249" in result[0].text


@pytest.mark.asyncio
async def test_storage_md5_failure(mock_flipper, mock_protobuf_rpc):
    mock_protobuf_rpc.storage_md5sum = AsyncMock(return_value=None)
    m = StorageModule(mock_flipper)
    result = await m.handle_tool_call("storage_md5", {"path": "/ext/missing.txt"})
    assert "could not" in result[0].text.lower()


# ── storage_info ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_storage_info_success(mock_flipper):
    m = StorageModule(mock_flipper)
    result = await m.handle_tool_call("storage_info", {"path": "/ext"})

    text = result[0].text
    assert "1,000,000" in text  # total
    assert "750,000" in text   # free
    assert "25.0%" in text     # used% = (total-free)/total = 250_000/1_000_000


@pytest.mark.asyncio
async def test_storage_info_failure(mock_flipper, mock_protobuf_rpc):
    mock_protobuf_rpc.storage_info = AsyncMock(return_value=None)
    m = StorageModule(mock_flipper)
    result = await m.handle_tool_call("storage_info", {"path": "/ext"})
    assert "could not" in result[0].text.lower()


# ── Unknown tool ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_storage_unknown_tool(mock_flipper):
    m = StorageModule(mock_flipper)
    result = await m.handle_tool_call("storage_nonexistent", {})
    assert "unknown" in result[0].text.lower()
