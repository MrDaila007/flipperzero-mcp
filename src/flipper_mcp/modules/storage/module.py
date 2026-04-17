"""Storage module for Flipper Zero MCP.

Provides full CRUD access to the device filesystem (/int and /ext).
"""

import base64
from typing import Any, List, Sequence

from mcp.types import Tool, TextContent

from ..base_module import FlipperModule


class StorageModule(FlipperModule):
    """Full filesystem access for Flipper Zero storage."""

    @property
    def name(self) -> str:
        return "storage"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Read, write, and manage files on Flipper Zero storage (/int and /ext)"

    def get_tools(self) -> List[Tool]:
        return [
            Tool(
                name="storage_list",
                description=(
                    "List files and directories at a path on the Flipper Zero. "
                    "Valid root paths: /int (internal flash), /ext (SD card). "
                    "Returns name, type (FILE/DIR), and size for each entry."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Directory path, e.g. /ext/apps or /int",
                        },
                        "include_md5": {
                            "type": "boolean",
                            "description": "Include MD5 checksums for files (slower)",
                            "default": False,
                        },
                    },
                    "required": ["path"],
                },
            ),
            Tool(
                name="storage_read",
                description=(
                    "Read a file from Flipper Zero storage. "
                    "Text files are returned as UTF-8 strings; "
                    "binary files are returned as base64-encoded strings."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path, e.g. /ext/badusb/script.txt",
                        },
                        "encoding": {
                            "type": "string",
                            "enum": ["auto", "utf8", "base64"],
                            "description": "Output encoding. auto = try UTF-8, fallback to base64",
                            "default": "auto",
                        },
                    },
                    "required": ["path"],
                },
            ),
            Tool(
                name="storage_write",
                description=(
                    "Write data to a file on Flipper Zero storage. "
                    "Creates parent directories automatically if needed."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Destination path, e.g. /ext/apps/test.txt",
                        },
                        "content": {
                            "type": "string",
                            "description": "File content (UTF-8 text or base64-encoded bytes)",
                        },
                        "encoding": {
                            "type": "string",
                            "enum": ["utf8", "base64"],
                            "description": "Content encoding",
                            "default": "utf8",
                        },
                    },
                    "required": ["path", "content"],
                },
            ),
            Tool(
                name="storage_mkdir",
                description="Create a directory on Flipper Zero storage.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Directory path to create"},
                    },
                    "required": ["path"],
                },
            ),
            Tool(
                name="storage_delete",
                description="Delete a file or directory from Flipper Zero storage.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to delete"},
                        "recursive": {
                            "type": "boolean",
                            "description": "Delete directory recursively",
                            "default": False,
                        },
                    },
                    "required": ["path"],
                },
            ),
            Tool(
                name="storage_rename",
                description="Rename or move a file or directory on Flipper Zero storage.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "old_path": {"type": "string", "description": "Current path"},
                        "new_path": {"type": "string", "description": "New path"},
                    },
                    "required": ["old_path", "new_path"],
                },
            ),
            Tool(
                name="storage_stat",
                description="Get metadata (type, size) for a file or directory without reading content.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to inspect"},
                    },
                    "required": ["path"],
                },
            ),
            Tool(
                name="storage_md5",
                description="Compute the MD5 checksum of a file on Flipper Zero storage.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path"},
                    },
                    "required": ["path"],
                },
            ),
            Tool(
                name="storage_info",
                description="Get total and free space for a storage volume (/int or /ext).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Storage volume: /int or /ext",
                        },
                    },
                    "required": ["path"],
                },
            ),
        ]

    async def handle_tool_call(
        self, tool_name: str, arguments: Any
    ) -> Sequence[TextContent]:
        handlers = {
            "storage_list": self._storage_list,
            "storage_read": self._storage_read,
            "storage_write": self._storage_write,
            "storage_mkdir": self._storage_mkdir,
            "storage_delete": self._storage_delete,
            "storage_rename": self._storage_rename,
            "storage_stat": self._storage_stat,
            "storage_md5": self._storage_md5,
            "storage_info": self._storage_info,
        }
        handler = handlers.get(tool_name)
        if handler is None:
            return [TextContent(type="text", text=f"Unknown storage tool: {tool_name}")]
        return await handler(arguments or {})

    # ── Tool implementations ──────────────────────────────────────────────────

    async def _storage_list(self, args: Any) -> Sequence[TextContent]:
        path = args.get("path", "/ext")
        include_md5 = bool(args.get("include_md5", False))
        try:
            rpc = self.flipper.rpc
            if not rpc or not rpc.protobuf_rpc:
                return [TextContent(type="text", text="Device not connected or RPC unavailable")]

            entries = await rpc.protobuf_rpc.storage_list_detailed(path, include_md5=include_md5)
            if not entries:
                return [TextContent(type="text", text=f"Directory '{path}' is empty or does not exist")]

            lines = [f"Contents of {path}:", ""]
            for e in entries:
                size_str = f"  {e['size']:>10} B" if e["type"] == "FILE" else "         DIR"
                md5_str = f"  md5:{e['md5sum']}" if "md5sum" in e else ""
                lines.append(f"  [{e['type']}] {e['name']}{size_str}{md5_str}")
            lines.append(f"\n{len(entries)} entries")
            return [TextContent(type="text", text="\n".join(lines))]
        except Exception as ex:
            return [TextContent(type="text", text=f"storage_list error: {ex}")]

    async def _storage_read(self, args: Any) -> Sequence[TextContent]:
        path = args.get("path", "")
        encoding = args.get("encoding", "auto")
        try:
            rpc = self.flipper.rpc
            if not rpc or not rpc.protobuf_rpc:
                return [TextContent(type="text", text="Device not connected or RPC unavailable")]

            raw: bytes = await rpc.protobuf_rpc.storage_read(path)
            if not raw:
                return [TextContent(type="text", text=f"File '{path}' is empty or does not exist")]

            if encoding == "base64":
                content = base64.b64encode(raw).decode("ascii")
                return [TextContent(type="text", text=f"File: {path} ({len(raw)} bytes, base64)\n\n{content}")]

            if encoding == "utf8":
                return [TextContent(type="text", text=f"File: {path} ({len(raw)} bytes)\n\n{raw.decode('utf-8', errors='replace')}")]

            # auto: try UTF-8, fallback to base64
            try:
                text = raw.decode("utf-8")
                return [TextContent(type="text", text=f"File: {path} ({len(raw)} bytes)\n\n{text}")]
            except UnicodeDecodeError:
                content = base64.b64encode(raw).decode("ascii")
                return [TextContent(type="text", text=f"File: {path} ({len(raw)} bytes, binary → base64)\n\n{content}")]
        except Exception as ex:
            return [TextContent(type="text", text=f"storage_read error: {ex}")]

    async def _storage_write(self, args: Any) -> Sequence[TextContent]:
        path = args.get("path", "")
        content = args.get("content", "")
        encoding = args.get("encoding", "utf8")
        try:
            rpc = self.flipper.rpc
            if not rpc or not rpc.protobuf_rpc:
                return [TextContent(type="text", text="Device not connected or RPC unavailable")]

            if encoding == "base64":
                data = base64.b64decode(content)
            else:
                data = content.encode("utf-8")

            ok = await rpc.protobuf_rpc.storage_write(path, data)
            if ok:
                return [TextContent(type="text", text=f"Written {len(data)} bytes to {path}")]
            return [TextContent(type="text", text=f"Failed to write to {path}")]
        except Exception as ex:
            return [TextContent(type="text", text=f"storage_write error: {ex}")]

    async def _storage_mkdir(self, args: Any) -> Sequence[TextContent]:
        path = args.get("path", "")
        try:
            rpc = self.flipper.rpc
            if not rpc or not rpc.protobuf_rpc:
                return [TextContent(type="text", text="Device not connected or RPC unavailable")]

            ok = await rpc.protobuf_rpc.storage_mkdir(path)
            if ok:
                return [TextContent(type="text", text=f"Directory created: {path}")]
            return [TextContent(type="text", text=f"Failed to create directory: {path}")]
        except Exception as ex:
            return [TextContent(type="text", text=f"storage_mkdir error: {ex}")]

    async def _storage_delete(self, args: Any) -> Sequence[TextContent]:
        path = args.get("path", "")
        recursive = bool(args.get("recursive", False))
        try:
            rpc = self.flipper.rpc
            if not rpc or not rpc.protobuf_rpc:
                return [TextContent(type="text", text="Device not connected or RPC unavailable")]

            ok = await rpc.protobuf_rpc.storage_delete(path, recursive=recursive)
            if ok:
                return [TextContent(type="text", text=f"Deleted: {path}")]
            return [TextContent(type="text", text=f"Failed to delete: {path}")]
        except Exception as ex:
            return [TextContent(type="text", text=f"storage_delete error: {ex}")]

    async def _storage_rename(self, args: Any) -> Sequence[TextContent]:
        old_path = args.get("old_path", "")
        new_path = args.get("new_path", "")
        try:
            rpc = self.flipper.rpc
            if not rpc or not rpc.protobuf_rpc:
                return [TextContent(type="text", text="Device not connected or RPC unavailable")]

            ok = await rpc.protobuf_rpc.storage_rename(old_path, new_path)
            if ok:
                return [TextContent(type="text", text=f"Renamed: {old_path} -> {new_path}")]
            return [TextContent(type="text", text=f"Failed to rename: {old_path}")]
        except Exception as ex:
            return [TextContent(type="text", text=f"storage_rename error: {ex}")]

    async def _storage_stat(self, args: Any) -> Sequence[TextContent]:
        path = args.get("path", "")
        try:
            rpc = self.flipper.rpc
            if not rpc or not rpc.protobuf_rpc:
                return [TextContent(type="text", text="Device not connected or RPC unavailable")]

            info = await rpc.protobuf_rpc.storage_stat(path)
            if info:
                lines = [
                    f"Path:  {path}",
                    f"Type:  {info['type']}",
                    f"Name:  {info.get('name', '')}",
                ]
                if info["type"] == "FILE":
                    lines.append(f"Size:  {info['size']} bytes")
                return [TextContent(type="text", text="\n".join(lines))]
            return [TextContent(type="text", text=f"Path not found: {path}")]
        except Exception as ex:
            return [TextContent(type="text", text=f"storage_stat error: {ex}")]

    async def _storage_md5(self, args: Any) -> Sequence[TextContent]:
        path = args.get("path", "")
        try:
            rpc = self.flipper.rpc
            if not rpc or not rpc.protobuf_rpc:
                return [TextContent(type="text", text="Device not connected or RPC unavailable")]

            md5 = await rpc.protobuf_rpc.storage_md5sum(path)
            if md5:
                return [TextContent(type="text", text=f"MD5 ({path}): {md5}")]
            return [TextContent(type="text", text=f"Could not compute MD5 for: {path}")]
        except Exception as ex:
            return [TextContent(type="text", text=f"storage_md5 error: {ex}")]

    async def _storage_info(self, args: Any) -> Sequence[TextContent]:
        path = args.get("path", "/ext")
        try:
            rpc = self.flipper.rpc
            if not rpc or not rpc.protobuf_rpc:
                return [TextContent(type="text", text="Device not connected or RPC unavailable")]

            info = await rpc.protobuf_rpc.storage_info(path)
            if info:
                total = info[0]
                free = info[1]
                used = total - free
                pct = (used / total * 100) if total else 0
                return [TextContent(
                    type="text",
                    text=(
                        f"Storage info: {path}\n"
                        f"  Total: {total:,} bytes ({total // 1024 // 1024} MB)\n"
                        f"  Used:  {used:,} bytes ({pct:.1f}%)\n"
                        f"  Free:  {free:,} bytes"
                    ),
                )]
            return [TextContent(type="text", text=f"Could not get storage info for: {path}")]
        except Exception as ex:
            return [TextContent(type="text", text=f"storage_info error: {ex}")]
