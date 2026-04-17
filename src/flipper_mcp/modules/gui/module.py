"""GUI / Screen module for Flipper Zero MCP.

Provides screen capture (PNG), hardware button input, and navigation helpers.

Screen frame format notes
--------------------------
The Flipper Zero sends 128×64 = 1024 bytes in row-major format:
  - Each row occupies 16 bytes (128 pixels / 8 bits per byte)
  - Within each byte: bit 0 (LSB) = leftmost pixel
  - Total layout: byte[y * 16 + x // 8], bit[x % 8] → pixel(x, y)

PIL Image.frombytes('1', ...) uses MSB-first packing, so bits must be
reversed in each byte before passing to PIL.
"""

import asyncio
import base64
import io
from typing import Any, List, Sequence

from mcp.types import Tool, TextContent

from ..base_module import FlipperModule

# Precomputed bit-reversal lookup table (LSB-first ↔ MSB-first)
_REVERSE_BITS = bytes(int(f"{b:08b}"[::-1], 2) for b in range(256))

VALID_KEYS = {"UP", "DOWN", "LEFT", "RIGHT", "OK", "BACK"}
VALID_TYPES = {"PRESS", "RELEASE", "SHORT", "LONG", "REPEAT"}


def _raw_to_png(data: bytes, scale: int = 2) -> bytes:
    """Convert raw 1024-byte row-major frame to PNG bytes."""
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError("Pillow is required for screen capture. Run: pip install pillow")

    if len(data) != 1024:
        raise ValueError(f"Expected 1024 bytes, got {len(data)}")

    # Reverse bit order in each byte so PIL MSB=leftmost convention is satisfied
    rev = bytes(_REVERSE_BITS[b] for b in data)

    img = Image.frombytes("1", (128, 64), rev)
    if scale > 1:
        img = img.resize((128 * scale, 64 * scale), Image.Resampling.NEAREST)

    # Convert to RGB palette (white background, black pixels) for nicer PNG
    rgb = Image.new("RGB", img.size, (255, 255, 255))
    mask = img.convert("L")
    # Pixels that are 0 in '1' mode = black in the display → black in RGB
    black_layer = Image.new("RGB", img.size, (0, 0, 0))
    # '1' mode: 0=black, 255=white after convert to L → invert for mask
    from PIL import ImageOps
    inv_mask = ImageOps.invert(mask)
    rgb.paste(black_layer, mask=inv_mask)

    buf = io.BytesIO()
    rgb.save(buf, format="PNG")
    return buf.getvalue()


class GuiModule(FlipperModule):
    """Screen capture and hardware input for Flipper Zero."""

    @property
    def name(self) -> str:
        return "gui"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Capture Flipper Zero screen as PNG and send hardware button inputs"

    def validate_environment(self) -> tuple[bool, str]:
        try:
            import PIL  # noqa: F401
            return True, ""
        except ImportError:
            return False, "Pillow library not installed. Run: pip install pillow"

    def get_tools(self) -> List[Tool]:
        return [
            Tool(
                name="gui_screen_capture",
                description=(
                    "Capture the current Flipper Zero screen as a PNG image. "
                    "Returns a base64-encoded PNG (128×64 px, scaled 2× by default). "
                    "Starts and stops screen streaming automatically."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "scale": {
                            "type": "integer",
                            "description": "Scale factor for the output PNG (1 = 128×64, 2 = 256×128)",
                            "default": 2,
                            "minimum": 1,
                            "maximum": 8,
                        },
                    },
                    "required": [],
                },
            ),
            Tool(
                name="gui_send_input",
                description=(
                    "Send a hardware button input event to the Flipper Zero. "
                    "Keys: UP, DOWN, LEFT, RIGHT, OK, BACK. "
                    "Types: PRESS, RELEASE, SHORT (default), LONG, REPEAT."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "key": {
                            "type": "string",
                            "enum": ["UP", "DOWN", "LEFT", "RIGHT", "OK", "BACK"],
                            "description": "Button to press",
                        },
                        "type": {
                            "type": "string",
                            "enum": ["PRESS", "RELEASE", "SHORT", "LONG", "REPEAT"],
                            "description": "Input event type",
                            "default": "SHORT",
                        },
                    },
                    "required": ["key"],
                },
            ),
            Tool(
                name="gui_navigate",
                description=(
                    "Send a sequence of hardware button presses with a configurable "
                    "delay between each. Useful for scripting menu navigation. "
                    "Example: ['UP', 'UP', 'OK'] navigates up twice then confirms."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "sequence": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["UP", "DOWN", "LEFT", "RIGHT", "OK", "BACK"],
                            },
                            "description": "List of button presses to send in order",
                            "minItems": 1,
                        },
                        "delay_ms": {
                            "type": "integer",
                            "description": "Delay between button presses in milliseconds",
                            "default": 200,
                            "minimum": 0,
                            "maximum": 5000,
                        },
                        "type": {
                            "type": "string",
                            "enum": ["PRESS", "RELEASE", "SHORT", "LONG", "REPEAT"],
                            "description": "Input event type for all buttons in sequence",
                            "default": "SHORT",
                        },
                    },
                    "required": ["sequence"],
                },
            ),
        ]

    async def handle_tool_call(
        self, tool_name: str, arguments: Any
    ) -> Sequence[TextContent]:
        handlers = {
            "gui_screen_capture": self._screen_capture,
            "gui_send_input": self._send_input,
            "gui_navigate": self._navigate,
        }
        handler = handlers.get(tool_name)
        if handler is None:
            return [TextContent(type="text", text=f"Unknown gui tool: {tool_name}")]
        return await handler(arguments or {})

    # ── Tool implementations ──────────────────────────────────────────────────

    def _get_rpc(self) -> Any:
        rpc = self.flipper.rpc
        if rpc and rpc.protobuf_rpc:
            return rpc.protobuf_rpc
        return None

    async def _screen_capture(self, args: Any) -> Sequence[TextContent]:
        scale = int(args.get("scale", 2))
        scale = max(1, min(scale, 8))
        try:
            pb = self._get_rpc()
            if pb is None:
                return [TextContent(type="text", text="Device not connected or RPC unavailable")]

            frame = await pb.gui_capture_screen_frame(timeout=8.0)
            if frame is None:
                return [TextContent(
                    type="text",
                    text=(
                        "Could not capture screen frame. Possible reasons:\n"
                        "  - Device is in DFU/recovery mode (no GUI)\n"
                        "  - Screen streaming not supported on this firmware\n"
                        "  - Timeout waiting for frame"
                    ),
                )]

            png_bytes = _raw_to_png(frame["data"], scale=scale)
            b64 = base64.b64encode(png_bytes).decode("ascii")
            orientation_names = {0: "HORIZONTAL", 1: "HORIZONTAL_FLIP", 2: "VERTICAL", 3: "VERTICAL_FLIP"}
            orient = orientation_names.get(frame["orientation"], str(frame["orientation"]))
            w, h = 128 * scale, 64 * scale

            return [TextContent(
                type="text",
                text=(
                    f"Screen captured: {w}×{h} px, orientation={orient}\n"
                    f"PNG (base64):\n{b64}"
                ),
            )]
        except RuntimeError as ex:
            return [TextContent(type="text", text=str(ex))]
        except Exception as ex:
            return [TextContent(type="text", text=f"gui_screen_capture error: {ex}")]

    async def _send_input(self, args: Any) -> Sequence[TextContent]:
        key = str(args.get("key", "")).upper()
        input_type = str(args.get("type", "SHORT")).upper()

        if key not in VALID_KEYS:
            return [TextContent(type="text", text=f"Invalid key '{key}'. Valid: {', '.join(sorted(VALID_KEYS))}")]
        if input_type not in VALID_TYPES:
            return [TextContent(type="text", text=f"Invalid type '{input_type}'. Valid: {', '.join(sorted(VALID_TYPES))}")]

        try:
            pb = self._get_rpc()
            if pb is None:
                return [TextContent(type="text", text="Device not connected or RPC unavailable")]

            ok = await pb.gui_send_input_event(key, input_type)
            if ok:
                return [TextContent(type="text", text=f"Input sent: {key} ({input_type})")]
            return [TextContent(type="text", text=f"Failed to send input: {key} ({input_type})")]
        except Exception as ex:
            return [TextContent(type="text", text=f"gui_send_input error: {ex}")]

    async def _navigate(self, args: Any) -> Sequence[TextContent]:
        sequence = args.get("sequence", [])
        delay_ms = int(args.get("delay_ms", 200))
        input_type = str(args.get("type", "SHORT")).upper()

        if not sequence:
            return [TextContent(type="text", text="sequence must not be empty")]
        if input_type not in VALID_TYPES:
            return [TextContent(type="text", text=f"Invalid type '{input_type}'")]

        invalid = [k for k in sequence if str(k).upper() not in VALID_KEYS]
        if invalid:
            return [TextContent(type="text", text=f"Invalid keys: {invalid}. Valid: {sorted(VALID_KEYS)}")]

        try:
            pb = self._get_rpc()
            if pb is None:
                return [TextContent(type="text", text="Device not connected or RPC unavailable")]

            sent = []
            failed = []
            for key in sequence:
                key = str(key).upper()
                ok = await pb.gui_send_input_event(key, input_type)
                if ok:
                    sent.append(key)
                else:
                    failed.append(key)
                if delay_ms > 0:
                    await asyncio.sleep(delay_ms / 1000.0)

            result = f"Navigation complete: {len(sent)}/{len(sequence)} inputs sent"
            if sent:
                result += f"\n  Sent: {' -> '.join(sent)}"
            if failed:
                result += f"\n  Failed: {failed}"
            return [TextContent(type="text", text=result)]
        except Exception as ex:
            return [TextContent(type="text", text=f"gui_navigate error: {ex}")]
