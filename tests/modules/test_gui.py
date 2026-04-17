"""Tests for the GUI / screen module."""

import base64
import io
import pytest
from unittest.mock import AsyncMock, MagicMock

from flipper_mcp.modules.gui.module import GuiModule, _raw_to_png, _REVERSE_BITS


def _no_rpc_client():
    client = MagicMock()
    client.rpc = None
    return client


# ── Pixel conversion helpers ──────────────────────────────────────────────────

def _make_frame(bit_value: int) -> bytes:
    """Create a 1024-byte frame where every pixel = bit_value (0 or 1)."""
    byte_val = 0xFF if bit_value else 0x00
    return bytes([byte_val] * 1024)


def _png_pixel(png_bytes: bytes, x: int, y: int) -> tuple:
    """Return (R, G, B) for pixel (x, y) in a PNG image."""
    from PIL import Image
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    return img.getpixel((x, y))


# ── _REVERSE_BITS table ───────────────────────────────────────────────────────

def test_reverse_bits_table_zero():
    assert _REVERSE_BITS[0x00] == 0x00


def test_reverse_bits_table_ff():
    assert _REVERSE_BITS[0xFF] == 0xFF


def test_reverse_bits_table_01():
    # 0b00000001 reversed = 0b10000000 = 0x80
    assert _REVERSE_BITS[0x01] == 0x80


def test_reverse_bits_table_80():
    # 0b10000000 reversed = 0b00000001 = 0x01
    assert _REVERSE_BITS[0x80] == 0x01


def test_reverse_bits_table_symmetry():
    """Reversing twice gives original byte."""
    for b in range(256):
        assert _REVERSE_BITS[_REVERSE_BITS[b]] == b


# ── _raw_to_png conversion ────────────────────────────────────────────────────

def test_raw_to_png_wrong_size():
    with pytest.raises(ValueError, match="1024"):
        _raw_to_png(bytes(100))


def test_raw_to_png_all_zeros_returns_valid_png():
    """All-zero frame → valid PNG without error."""
    png = _raw_to_png(_make_frame(0))
    assert png[:4] == b"\x89PNG"


def test_raw_to_png_all_ones_returns_valid_png():
    """All-ones frame → valid PNG without error."""
    png = _raw_to_png(_make_frame(1))
    assert png[:4] == b"\x89PNG"


def test_raw_to_png_scale_1_size():
    png = _raw_to_png(_make_frame(0), scale=1)
    from PIL import Image
    img = Image.open(io.BytesIO(png))
    assert img.size == (128, 64)


def test_raw_to_png_scale_2_size():
    png = _raw_to_png(_make_frame(0), scale=2)
    from PIL import Image
    img = Image.open(io.BytesIO(png))
    assert img.size == (256, 128)


def test_raw_to_png_scale_4_size():
    png = _raw_to_png(_make_frame(0), scale=4)
    from PIL import Image
    img = Image.open(io.BytesIO(png))
    assert img.size == (512, 256)


def test_raw_to_png_all_off_pixels_are_black():
    """Bit=0 (pixel OFF) should produce a black pixel in the PNG."""
    png = _raw_to_png(_make_frame(0), scale=1)
    r, g, b = _png_pixel(png, 0, 0)
    assert r == 0 and g == 0 and b == 0


def test_raw_to_png_all_on_pixels_are_white():
    """Bit=1 (pixel ON) should produce a white pixel in the PNG."""
    png = _raw_to_png(_make_frame(1), scale=1)
    r, g, b = _png_pixel(png, 0, 0)
    assert r == 255 and g == 255 and b == 255


def test_raw_to_png_single_pixel_top_left():
    """Only bit 0 of byte 0 set → pixel (0,0) should be white."""
    data = bytearray(1024)
    data[0] = 0x01  # bit 0 = pixel(0, 0)
    png = _raw_to_png(bytes(data), scale=1)

    assert _png_pixel(png, 0, 0) == (255, 255, 255)   # ON
    assert _png_pixel(png, 1, 0) == (0, 0, 0)          # OFF


def test_raw_to_png_second_pixel_in_row():
    """Bit 1 of byte 0 = pixel(1, 0)."""
    data = bytearray(1024)
    data[0] = 0x02  # bit 1 = pixel(1, 0)
    png = _raw_to_png(bytes(data), scale=1)

    assert _png_pixel(png, 0, 0) == (0, 0, 0)           # OFF
    assert _png_pixel(png, 1, 0) == (255, 255, 255)      # ON


def test_raw_to_png_first_pixel_second_row():
    """Byte 16 bit 0 = pixel(0, 1) (second row)."""
    data = bytearray(1024)
    data[16] = 0x01  # byte index = 1 * 16 + 0 = 16, bit 0
    png = _raw_to_png(bytes(data), scale=1)

    assert _png_pixel(png, 0, 0) == (0, 0, 0)           # row 0 is OFF
    assert _png_pixel(png, 0, 1) == (255, 255, 255)      # row 1, col 0 is ON


# ── Module meta ───────────────────────────────────────────────────────────────

def test_gui_module_properties(mock_flipper):
    m = GuiModule(mock_flipper)
    assert m.name == "gui"
    assert m.version == "1.0.0"
    assert "screen" in m.description.lower() or "gui" in m.description.lower()


def test_gui_tools(mock_flipper):
    tools = GuiModule(mock_flipper).get_tools()
    names = [t.name for t in tools]
    assert len(tools) == 3
    assert "gui_screen_capture" in names
    assert "gui_send_input" in names
    assert "gui_navigate" in names


def test_gui_validate_environment(mock_flipper):
    """Pillow is installed, so validate_environment should succeed."""
    m = GuiModule(mock_flipper)
    ok, msg = m.validate_environment()
    assert ok


# ── gui_screen_capture ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_screen_capture_success(mock_flipper, mock_protobuf_rpc):
    m = GuiModule(mock_flipper)
    result = await m.handle_tool_call("gui_screen_capture", {})

    text = result[0].text
    assert "PNG" in text or "png" in text.lower()
    # Should contain valid base64 PNG data
    b64_part = text.split("\n")[-1].strip()
    png_bytes = base64.b64decode(b64_part)
    assert png_bytes[:4] == b"\x89PNG"


@pytest.mark.asyncio
async def test_screen_capture_default_scale(mock_flipper):
    m = GuiModule(mock_flipper)
    result = await m.handle_tool_call("gui_screen_capture", {})

    assert "256" in result[0].text and "128" in result[0].text


@pytest.mark.asyncio
async def test_screen_capture_custom_scale(mock_flipper):
    m = GuiModule(mock_flipper)
    result = await m.handle_tool_call("gui_screen_capture", {"scale": 1})

    assert "128" in result[0].text and "64" in result[0].text


@pytest.mark.asyncio
async def test_screen_capture_no_frame(mock_flipper, mock_protobuf_rpc):
    mock_protobuf_rpc.gui_capture_screen_frame = AsyncMock(return_value=None)
    m = GuiModule(mock_flipper)
    result = await m.handle_tool_call("gui_screen_capture", {})

    text = result[0].text.lower()
    assert "could not" in text or "timeout" in text or "capture" in text


@pytest.mark.asyncio
async def test_screen_capture_no_rpc():
    m = GuiModule(_no_rpc_client())
    result = await m.handle_tool_call("gui_screen_capture", {})
    text = result[0].text.lower()
    assert "unavailable" in text or "not connected" in text


@pytest.mark.asyncio
async def test_screen_capture_orientation_in_output(mock_flipper, mock_protobuf_rpc):
    mock_protobuf_rpc.gui_capture_screen_frame = AsyncMock(return_value={
        "data": bytes(1024),
        "orientation": 1,  # HORIZONTAL_FLIP
    })
    m = GuiModule(mock_flipper)
    result = await m.handle_tool_call("gui_screen_capture", {})
    assert "HORIZONTAL_FLIP" in result[0].text


# ── gui_send_input ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_input_success(mock_flipper, mock_protobuf_rpc):
    m = GuiModule(mock_flipper)
    result = await m.handle_tool_call("gui_send_input", {"key": "OK"})

    assert "OK" in result[0].text
    mock_protobuf_rpc.gui_send_input_event.assert_awaited_once_with("OK", "SHORT")


@pytest.mark.asyncio
@pytest.mark.parametrize("key", ["UP", "DOWN", "LEFT", "RIGHT", "OK", "BACK"])
async def test_send_input_all_valid_keys(mock_flipper, key):
    m = GuiModule(mock_flipper)
    result = await m.handle_tool_call("gui_send_input", {"key": key})
    assert "sent" in result[0].text.lower() or key in result[0].text


@pytest.mark.asyncio
@pytest.mark.parametrize("itype", ["PRESS", "RELEASE", "SHORT", "LONG", "REPEAT"])
async def test_send_input_all_valid_types(mock_flipper, itype):
    m = GuiModule(mock_flipper)
    result = await m.handle_tool_call("gui_send_input", {"key": "OK", "type": itype})
    assert "sent" in result[0].text.lower() or itype in result[0].text


@pytest.mark.asyncio
async def test_send_input_invalid_key(mock_flipper):
    m = GuiModule(mock_flipper)
    result = await m.handle_tool_call("gui_send_input", {"key": "INVALID_KEY"})
    assert "invalid" in result[0].text.lower()


@pytest.mark.asyncio
async def test_send_input_invalid_type(mock_flipper):
    m = GuiModule(mock_flipper)
    result = await m.handle_tool_call("gui_send_input", {"key": "OK", "type": "SMASH"})
    assert "invalid" in result[0].text.lower()


@pytest.mark.asyncio
async def test_send_input_failure(mock_flipper, mock_protobuf_rpc):
    mock_protobuf_rpc.gui_send_input_event = AsyncMock(return_value=False)
    m = GuiModule(mock_flipper)
    result = await m.handle_tool_call("gui_send_input", {"key": "UP"})
    assert "failed" in result[0].text.lower()


# ── gui_navigate ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_navigate_success(mock_flipper, mock_protobuf_rpc):
    m = GuiModule(mock_flipper)
    result = await m.handle_tool_call("gui_navigate", {
        "sequence": ["UP", "DOWN", "OK"],
        "delay_ms": 0,
    })

    text = result[0].text
    assert "3/3" in text
    assert mock_protobuf_rpc.gui_send_input_event.await_count == 3


@pytest.mark.asyncio
async def test_navigate_reports_correct_sent_count(mock_flipper, mock_protobuf_rpc):
    # Make first call fail, rest succeed
    mock_protobuf_rpc.gui_send_input_event = AsyncMock(side_effect=[False, True, True])
    m = GuiModule(mock_flipper)
    result = await m.handle_tool_call("gui_navigate", {
        "sequence": ["UP", "OK", "BACK"],
        "delay_ms": 0,
    })

    assert "2/3" in result[0].text


@pytest.mark.asyncio
async def test_navigate_empty_sequence(mock_flipper):
    m = GuiModule(mock_flipper)
    result = await m.handle_tool_call("gui_navigate", {"sequence": []})
    assert "empty" in result[0].text.lower()


@pytest.mark.asyncio
async def test_navigate_invalid_key_in_sequence(mock_flipper):
    m = GuiModule(mock_flipper)
    result = await m.handle_tool_call("gui_navigate", {"sequence": ["UP", "NOPE"]})
    assert "invalid" in result[0].text.lower()


@pytest.mark.asyncio
async def test_navigate_uses_correct_input_type(mock_flipper, mock_protobuf_rpc):
    m = GuiModule(mock_flipper)
    await m.handle_tool_call("gui_navigate", {
        "sequence": ["OK"],
        "type": "LONG",
        "delay_ms": 0,
    })
    mock_protobuf_rpc.gui_send_input_event.assert_awaited_once_with("OK", "LONG")


@pytest.mark.asyncio
async def test_navigate_no_rpc():
    m = GuiModule(_no_rpc_client())
    result = await m.handle_tool_call("gui_navigate", {"sequence": ["OK"]})
    text = result[0].text.lower()
    assert "unavailable" in text or "not connected" in text


# ── Unknown tool ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gui_unknown_tool(mock_flipper):
    m = GuiModule(mock_flipper)
    result = await m.handle_tool_call("gui_nonexistent", {})
    assert "unknown" in result[0].text.lower()
