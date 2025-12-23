"""Basic Flipper Zero RPC protocol implementation.

This module implements a simplified RPC protocol for communicating with
Flipper Zero devices. The Flipper Zero uses a protobuf-based RPC protocol,
but for initial testing, we implement a basic CLI-based approach.
"""

import asyncio
import struct
from typing import Optional, Dict, Any, List
from .transport.base import FlipperTransport


class FlipperRPC:
    """
    Basic RPC client for Flipper Zero.
    
    Implements a simplified RPC protocol for basic operations.
    Note: Full protobuf RPC implementation would be more robust,
    but this provides basic functionality for testing.
    """
    
    def __init__(self, transport: FlipperTransport):
        """
        Initialize RPC client.
        
        Args:
            transport: Transport layer for communication
        """
        self.transport = transport
        self.command_id = 0
    
    async def send_command(self, command: str, data: bytes = b"") -> bytes:
        """
        Send a command to Flipper Zero.
        
        Note: This is a simplified implementation. The actual Flipper Zero
        uses a protobuf-based RPC protocol. This method may not work with
        all firmware versions and is primarily for basic connectivity testing.
        
        Args:
            command: Command string (e.g., "storage_list")
            data: Optional command data
            
        Returns:
            Response data (empty if no response or error)
        """
        try:
            # Simple command format: <command_len><command><data_len><data>
            cmd_bytes = command.encode('utf-8')
            cmd_len = len(cmd_bytes)
            data_len = len(data)
            
            # Build message: [4 bytes: cmd_len][cmd][4 bytes: data_len][data]
            message = struct.pack('>I', cmd_len) + cmd_bytes + struct.pack('>I', data_len) + data
            
            await self.transport.send(message)
            
            # Wait for response
            # Response format: [4 bytes: response_len][response_data]
            response_len_bytes = await self.transport.receive(timeout=2.0)
            if len(response_len_bytes) < 4:
                return b""
            
            response_len = struct.unpack('>I', response_len_bytes[:4])[0]
            if response_len == 0:
                return b""
            
            # Read the actual response
            response = await self.transport.receive(timeout=2.0)
            return response
        except Exception:
            # If structured RPC fails, return empty (will fall back to CLI methods)
            return b""
    
    async def ping(self) -> bool:
        """
        Ping the Flipper Zero to test connection.
        
        Returns:
            True if device responds
        """
        try:
            response = await self.send_command("ping")
            return len(response) > 0
        except Exception:
            return False
    
    async def get_device_info(self) -> Dict[str, Any]:
        """
        Get device information.
        
        Returns:
            Device info dictionary
        """
        try:
            response = await self.send_command("device_info")
            if response:
                # Parse response (simplified - would need proper parsing)
                info_str = response.decode('utf-8', errors='ignore')
                return {
                    "name": "Flipper Zero",
                    "firmware": info_str.split('\n')[0] if info_str else "Unknown",
                    "hardware": "Flipper Zero"
                }
        except Exception as e:
            pass
        
        # Fallback: try to read from CLI
        return await self._get_info_via_cli()
    
    async def _get_info_via_cli(self) -> Dict[str, Any]:
        """
        Get device info via CLI commands (fallback method).
        
        Note: Flipper Zero doesn't actually support simple text commands.
        This is a placeholder that returns basic info. In a full implementation,
        we would use the proper protobuf RPC protocol.
        """
        # For now, just return basic info since we can't easily query
        # without the full RPC protocol implementation
        return {
            "name": "Flipper Zero",
            "firmware": "Connected (RPC protocol not fully implemented)",
            "hardware": "Flipper Zero"
        }
    
    async def storage_list(self, path: str) -> List[str]:
        """
        List files in a directory.
        
        Args:
            path: Directory path (e.g., "/ext/badusb")
            
        Returns:
            List of filenames
        """
        try:
            # Try RPC command first
            path_bytes = path.encode('utf-8')
            response = await self.send_command("storage_list", path_bytes)
            
            if response:
                # Parse response - expect newline-separated filenames
                files_str = response.decode('utf-8', errors='ignore')
                files = [f.strip() for f in files_str.split('\n') if f.strip()]
                return files
        except Exception:
            pass
        
        # Fallback: try CLI approach
        return await self._storage_list_via_cli(path)
    
    async def _storage_list_via_cli(self, path: str) -> List[str]:
        """
        List files via CLI commands (fallback method).
        
        Note: This is a placeholder. The actual Flipper Zero requires
        the protobuf RPC protocol to list files. This method will return
        an empty list, indicating that the RPC protocol needs to be
        fully implemented for file operations.
        """
        # Without the full RPC protocol, we can't actually list files
        # This would require implementing the protobuf message format
        return []
    
    async def storage_read(self, path: str) -> str:
        """
        Read file contents.
        
        Args:
            path: File path (e.g., "/ext/badusb/test.txt")
            
        Returns:
            File contents as string
        """
        try:
            # Try RPC command first
            path_bytes = path.encode('utf-8')
            response = await self.send_command("storage_read", path_bytes)
            
            if response:
                return response.decode('utf-8', errors='ignore')
        except Exception:
            pass
        
        # Fallback: try CLI approach
        return await self._storage_read_via_cli(path)
    
    async def _storage_read_via_cli(self, path: str) -> str:
        """
        Read file via CLI commands (fallback method).
        
        Note: This is a placeholder. The actual Flipper Zero requires
        the protobuf RPC protocol to read files. This method will return
        an empty string, indicating that the RPC protocol needs to be
        fully implemented for file operations.
        """
        # Without the full RPC protocol, we can't actually read files
        # This would require implementing the protobuf message format
        return ""

