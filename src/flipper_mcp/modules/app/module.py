"""App control module for Flipper Zero MCP.

Provides full application lifecycle management: start, exit, load files,
send button events, exchange data, and inspect error state.
"""

import base64
from typing import Any, List, Sequence

from mcp.types import Tool, TextContent

from ..base_module import FlipperModule


class AppModule(FlipperModule):
    """Application lifecycle and control for Flipper Zero."""

    @property
    def name(self) -> str:
        return "app"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Launch, control, and debug applications running on Flipper Zero"

    def get_tools(self) -> List[Tool]:
        return [
            Tool(
                name="app_start",
                description=(
                    "Launch a Flipper Zero application by its FAP app ID "
                    "(e.g. 'snake_game', 'nfc', 'subghz'). "
                    "Optionally pass a string argument to the application."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "app_id": {
                            "type": "string",
                            "description": "Application ID, e.g. 'snake_game' or 'nfc'",
                        },
                        "args": {
                            "type": "string",
                            "description": "Optional argument string passed to the app",
                            "default": "",
                        },
                    },
                    "required": ["app_id"],
                },
            ),
            Tool(
                name="app_exit",
                description="Request the currently running application to exit.",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="app_load_file",
                description=(
                    "Instruct the currently running application to load a file "
                    "from device storage. Used for apps that accept a file path "
                    "(e.g. IR remote, NFC reader)."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path on device, e.g. /ext/infrared/tv.ir",
                        },
                    },
                    "required": ["path"],
                },
            ),
            Tool(
                name="app_lock_status",
                description=(
                    "Check whether any application is currently running "
                    "(holding the system lock)."
                ),
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="app_get_error",
                description=(
                    "Retrieve the last error code and message from the running "
                    "application. Useful for debugging crashes or assertion failures."
                ),
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="app_button_press",
                description=(
                    "Send an application-level button press event with a custom "
                    "string argument. This uses the PB_App_AppButtonPressRequest "
                    "channel (not a hardware key event)."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "args": {
                            "type": "string",
                            "description": "Argument string sent with the button press (up to 512 bytes)",
                            "default": "",
                        },
                        "index": {
                            "type": "integer",
                            "description": "Button index (application-defined)",
                            "default": 0,
                        },
                    },
                    "required": [],
                },
            ),
            Tool(
                name="app_button_release",
                description="Send an application-level button release event.",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="app_data_exchange",
                description=(
                    "Send raw bytes to the running application via the DataExchange "
                    "RPC channel. The application must implement the corresponding handler."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "string",
                            "description": "Base64-encoded bytes to send",
                        },
                    },
                    "required": ["data"],
                },
            ),
        ]

    async def handle_tool_call(
        self, tool_name: str, arguments: Any
    ) -> Sequence[TextContent]:
        handlers = {
            "app_start": self._app_start,
            "app_exit": self._app_exit,
            "app_load_file": self._app_load_file,
            "app_lock_status": self._app_lock_status,
            "app_get_error": self._app_get_error,
            "app_button_press": self._app_button_press,
            "app_button_release": self._app_button_release,
            "app_data_exchange": self._app_data_exchange,
        }
        handler = handlers.get(tool_name)
        if handler is None:
            return [TextContent(type="text", text=f"Unknown app tool: {tool_name}")]
        return await handler(arguments or {})

    # ── Tool implementations ──────────────────────────────────────────────────

    def _get_rpc(self):
        rpc = self.flipper.rpc
        if rpc and rpc.protobuf_rpc:
            return rpc.protobuf_rpc
        return None

    async def _app_start(self, args: Any) -> Sequence[TextContent]:
        app_id = args.get("app_id", "")
        app_args = args.get("args", "")
        if not app_id:
            return [TextContent(type="text", text="app_id is required")]
        try:
            pb = self._get_rpc()
            if pb is None:
                return [TextContent(type="text", text="Device not connected or RPC unavailable")]

            ok = await pb.app_start(app_id, args=app_args)
            if ok:
                msg = f"Started app: {app_id}"
                if app_args:
                    msg += f" (args: {app_args!r})"
                return [TextContent(type="text", text=msg)]
            return [TextContent(
                type="text",
                text=(
                    f"Failed to start app '{app_id}'. Possible reasons:\n"
                    "  - App ID is incorrect\n"
                    "  - Another app is already running (use app_lock_status to check)\n"
                    "  - App is not installed on the device"
                ),
            )]
        except Exception as ex:
            return [TextContent(type="text", text=f"app_start error: {ex}")]

    async def _app_exit(self, args: Any) -> Sequence[TextContent]:
        try:
            pb = self._get_rpc()
            if pb is None:
                return [TextContent(type="text", text="Device not connected or RPC unavailable")]

            ok = await pb.app_exit()
            if ok:
                return [TextContent(type="text", text="App exit requested successfully")]
            return [TextContent(type="text", text="Failed to request app exit (no app running?)")]
        except Exception as ex:
            return [TextContent(type="text", text=f"app_exit error: {ex}")]

    async def _app_load_file(self, args: Any) -> Sequence[TextContent]:
        path = args.get("path", "")
        if not path:
            return [TextContent(type="text", text="path is required")]
        try:
            pb = self._get_rpc()
            if pb is None:
                return [TextContent(type="text", text="Device not connected or RPC unavailable")]

            ok = await pb.app_load_file(path)
            if ok:
                return [TextContent(type="text", text=f"App loaded file: {path}")]
            return [TextContent(type="text", text=f"Failed to load file: {path}")]
        except Exception as ex:
            return [TextContent(type="text", text=f"app_load_file error: {ex}")]

    async def _app_lock_status(self, args: Any) -> Sequence[TextContent]:
        try:
            pb = self._get_rpc()
            if pb is None:
                return [TextContent(type="text", text="Device not connected or RPC unavailable")]

            locked = await pb.app_lock_status()
            if locked is None:
                return [TextContent(type="text", text="Could not determine lock status")]
            status = "LOCKED (an app is running)" if locked else "UNLOCKED (no app running)"
            return [TextContent(type="text", text=f"System lock status: {status}")]
        except Exception as ex:
            return [TextContent(type="text", text=f"app_lock_status error: {ex}")]

    async def _app_get_error(self, args: Any) -> Sequence[TextContent]:
        try:
            pb = self._get_rpc()
            if pb is None:
                return [TextContent(type="text", text="Device not connected or RPC unavailable")]

            err = await pb.app_get_error()
            if err is None:
                return [TextContent(type="text", text="Could not get app error (no app running?)")]
            if err["code"] == 0 and not err["text"]:
                return [TextContent(type="text", text="No error reported by current app")]
            return [TextContent(
                type="text",
                text=f"App error:\n  Code: {err['code']}\n  Text: {err['text'] or '(none)'}",
            )]
        except Exception as ex:
            return [TextContent(type="text", text=f"app_get_error error: {ex}")]

    async def _app_button_press(self, args: Any) -> Sequence[TextContent]:
        btn_args = args.get("args", "")
        index = int(args.get("index", 0))
        try:
            pb = self._get_rpc()
            if pb is None:
                return [TextContent(type="text", text="Device not connected or RPC unavailable")]

            ok = await pb.app_button_press(args=btn_args, index=index)
            if ok:
                return [TextContent(type="text", text=f"Button press sent (args={btn_args!r}, index={index})")]
            return [TextContent(type="text", text="Failed to send button press (no app running?)")]
        except Exception as ex:
            return [TextContent(type="text", text=f"app_button_press error: {ex}")]

    async def _app_button_release(self, args: Any) -> Sequence[TextContent]:
        try:
            pb = self._get_rpc()
            if pb is None:
                return [TextContent(type="text", text="Device not connected or RPC unavailable")]

            ok = await pb.app_button_release()
            if ok:
                return [TextContent(type="text", text="Button release sent")]
            return [TextContent(type="text", text="Failed to send button release")]
        except Exception as ex:
            return [TextContent(type="text", text=f"app_button_release error: {ex}")]

    async def _app_data_exchange(self, args: Any) -> Sequence[TextContent]:
        data_b64 = args.get("data", "")
        if not data_b64:
            return [TextContent(type="text", text="data (base64) is required")]
        try:
            data = base64.b64decode(data_b64)
        except Exception:
            return [TextContent(type="text", text="data must be valid base64")]
        try:
            pb = self._get_rpc()
            if pb is None:
                return [TextContent(type="text", text="Device not connected or RPC unavailable")]

            ok = await pb.app_data_exchange(data)
            if ok:
                return [TextContent(type="text", text=f"Sent {len(data)} bytes to app")]
            return [TextContent(type="text", text="Failed to send data (no app running?)")]
        except Exception as ex:
            return [TextContent(type="text", text=f"app_data_exchange error: {ex}")]
