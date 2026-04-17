"""Tests for the App control module."""

import base64
import pytest
from unittest.mock import AsyncMock, MagicMock

from flipper_mcp.modules.app.module import AppModule


def _no_rpc_client():
    client = MagicMock()
    client.rpc = None
    return client


# ── Module meta ───────────────────────────────────────────────────────────────

def test_app_module_properties(mock_flipper):
    m = AppModule(mock_flipper)
    assert m.name == "app"
    assert m.version == "1.0.0"
    assert "app" in m.description.lower()


def test_app_tools(mock_flipper):
    tools = AppModule(mock_flipper).get_tools()
    names = [t.name for t in tools]
    assert len(tools) == 8
    for expected in [
        "app_start", "app_exit", "app_load_file", "app_lock_status",
        "app_get_error", "app_button_press", "app_button_release", "app_data_exchange",
    ]:
        assert expected in names


# ── app_start ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_app_start_success(mock_flipper, mock_protobuf_rpc):
    m = AppModule(mock_flipper)
    result = await m.handle_tool_call("app_start", {"app_id": "snake_game"})

    assert "snake_game" in result[0].text
    assert "started" in result[0].text.lower()
    mock_protobuf_rpc.app_start.assert_awaited_once_with("snake_game", args="")


@pytest.mark.asyncio
async def test_app_start_with_args(mock_flipper, mock_protobuf_rpc):
    m = AppModule(mock_flipper)
    await m.handle_tool_call("app_start", {"app_id": "nfc", "args": "/ext/nfc/card.nfc"})
    mock_protobuf_rpc.app_start.assert_awaited_once_with("nfc", args="/ext/nfc/card.nfc")


@pytest.mark.asyncio
async def test_app_start_failure(mock_flipper, mock_protobuf_rpc):
    mock_protobuf_rpc.app_start = AsyncMock(return_value=False)
    m = AppModule(mock_flipper)
    result = await m.handle_tool_call("app_start", {"app_id": "bad_app"})

    assert "failed" in result[0].text.lower()
    # Should hint about possible causes
    assert "running" in result[0].text.lower() or "installed" in result[0].text.lower()


@pytest.mark.asyncio
async def test_app_start_missing_app_id(mock_flipper):
    m = AppModule(mock_flipper)
    result = await m.handle_tool_call("app_start", {})
    assert "required" in result[0].text.lower()


@pytest.mark.asyncio
async def test_app_start_no_rpc():
    m = AppModule(_no_rpc_client())
    result = await m.handle_tool_call("app_start", {"app_id": "nfc"})
    assert "unavailable" in result[0].text.lower() or "not connected" in result[0].text.lower()


# ── app_exit ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_app_exit_success(mock_flipper):
    m = AppModule(mock_flipper)
    result = await m.handle_tool_call("app_exit", {})

    assert "exit" in result[0].text.lower()
    assert "success" in result[0].text.lower() or "requested" in result[0].text.lower()


@pytest.mark.asyncio
async def test_app_exit_failure(mock_flipper, mock_protobuf_rpc):
    mock_protobuf_rpc.app_exit = AsyncMock(return_value=False)
    m = AppModule(mock_flipper)
    result = await m.handle_tool_call("app_exit", {})
    assert "failed" in result[0].text.lower()


# ── app_load_file ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_app_load_file_success(mock_flipper, mock_protobuf_rpc):
    m = AppModule(mock_flipper)
    result = await m.handle_tool_call("app_load_file", {"path": "/ext/infrared/tv.ir"})

    assert "/ext/infrared/tv.ir" in result[0].text
    mock_protobuf_rpc.app_load_file.assert_awaited_once_with("/ext/infrared/tv.ir")


@pytest.mark.asyncio
async def test_app_load_file_missing_path(mock_flipper):
    m = AppModule(mock_flipper)
    result = await m.handle_tool_call("app_load_file", {})
    assert "required" in result[0].text.lower()


@pytest.mark.asyncio
async def test_app_load_file_failure(mock_flipper, mock_protobuf_rpc):
    mock_protobuf_rpc.app_load_file = AsyncMock(return_value=False)
    m = AppModule(mock_flipper)
    result = await m.handle_tool_call("app_load_file", {"path": "/ext/missing.ir"})
    assert "failed" in result[0].text.lower()


# ── app_lock_status ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_app_lock_status_unlocked(mock_flipper):
    m = AppModule(mock_flipper)
    result = await m.handle_tool_call("app_lock_status", {})
    assert "unlocked" in result[0].text.lower()


@pytest.mark.asyncio
async def test_app_lock_status_locked(mock_flipper, mock_protobuf_rpc):
    mock_protobuf_rpc.app_lock_status = AsyncMock(return_value=True)
    m = AppModule(mock_flipper)
    result = await m.handle_tool_call("app_lock_status", {})
    assert "locked" in result[0].text.lower()


@pytest.mark.asyncio
async def test_app_lock_status_none(mock_flipper, mock_protobuf_rpc):
    mock_protobuf_rpc.app_lock_status = AsyncMock(return_value=None)
    m = AppModule(mock_flipper)
    result = await m.handle_tool_call("app_lock_status", {})
    assert "could not" in result[0].text.lower() or "determine" in result[0].text.lower()


# ── app_get_error ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_app_get_error_no_error(mock_flipper):
    m = AppModule(mock_flipper)
    result = await m.handle_tool_call("app_get_error", {})
    assert "no error" in result[0].text.lower()


@pytest.mark.asyncio
async def test_app_get_error_with_error(mock_flipper, mock_protobuf_rpc):
    mock_protobuf_rpc.app_get_error = AsyncMock(return_value={"code": 42, "text": "assertion failed"})
    m = AppModule(mock_flipper)
    result = await m.handle_tool_call("app_get_error", {})

    assert "42" in result[0].text
    assert "assertion failed" in result[0].text


@pytest.mark.asyncio
async def test_app_get_error_none_response(mock_flipper, mock_protobuf_rpc):
    mock_protobuf_rpc.app_get_error = AsyncMock(return_value=None)
    m = AppModule(mock_flipper)
    result = await m.handle_tool_call("app_get_error", {})
    assert "could not" in result[0].text.lower() or "no app" in result[0].text.lower()


# ── app_button_press / release ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_app_button_press_success(mock_flipper, mock_protobuf_rpc):
    m = AppModule(mock_flipper)
    result = await m.handle_tool_call("app_button_press", {"args": "confirm", "index": 1})

    assert "sent" in result[0].text.lower()
    mock_protobuf_rpc.app_button_press.assert_awaited_once_with(args="confirm", index=1)


@pytest.mark.asyncio
async def test_app_button_press_failure(mock_flipper, mock_protobuf_rpc):
    mock_protobuf_rpc.app_button_press = AsyncMock(return_value=False)
    m = AppModule(mock_flipper)
    result = await m.handle_tool_call("app_button_press", {})
    assert "failed" in result[0].text.lower()


@pytest.mark.asyncio
async def test_app_button_release_success(mock_flipper):
    m = AppModule(mock_flipper)
    result = await m.handle_tool_call("app_button_release", {})
    assert "sent" in result[0].text.lower() or "release" in result[0].text.lower()


@pytest.mark.asyncio
async def test_app_button_release_failure(mock_flipper, mock_protobuf_rpc):
    mock_protobuf_rpc.app_button_release = AsyncMock(return_value=False)
    m = AppModule(mock_flipper)
    result = await m.handle_tool_call("app_button_release", {})
    assert "failed" in result[0].text.lower()


# ── app_data_exchange ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_app_data_exchange_success(mock_flipper, mock_protobuf_rpc):
    payload = b"\x01\x02\x03"
    m = AppModule(mock_flipper)
    result = await m.handle_tool_call("app_data_exchange", {
        "data": base64.b64encode(payload).decode()
    })

    assert "3" in result[0].text
    mock_protobuf_rpc.app_data_exchange.assert_awaited_once_with(payload)


@pytest.mark.asyncio
async def test_app_data_exchange_invalid_base64(mock_flipper):
    m = AppModule(mock_flipper)
    result = await m.handle_tool_call("app_data_exchange", {"data": "not-valid-base64!!!"})
    assert "base64" in result[0].text.lower()


@pytest.mark.asyncio
async def test_app_data_exchange_missing_data(mock_flipper):
    m = AppModule(mock_flipper)
    result = await m.handle_tool_call("app_data_exchange", {})
    assert "required" in result[0].text.lower()


@pytest.mark.asyncio
async def test_app_data_exchange_failure(mock_flipper, mock_protobuf_rpc):
    mock_protobuf_rpc.app_data_exchange = AsyncMock(return_value=False)
    m = AppModule(mock_flipper)
    result = await m.handle_tool_call("app_data_exchange", {
        "data": base64.b64encode(b"test").decode()
    })
    assert "failed" in result[0].text.lower()


# ── Unknown tool ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_app_unknown_tool(mock_flipper):
    m = AppModule(mock_flipper)
    result = await m.handle_tool_call("app_nonexistent", {})
    assert "unknown" in result[0].text.lower()
