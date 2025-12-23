"""Flipper Zero RPC client wrapper."""

from typing import Any, Optional
from .transport.base import FlipperTransport
from .rpc import FlipperRPC


class FlipperStorage:
    """
    Storage operations wrapper.
    
    Provides file system operations on Flipper Zero.
    """
    
    def __init__(self, client: 'FlipperClient'):
        self.client = client
    
    async def list(self, path: str) -> list[str]:
        """
        List files in directory.
        
        Args:
            path: Directory path
            
        Returns:
            List of filenames
        """
        if not self.client.rpc:
            return []
        return await self.client.rpc.storage_list(path)
    
    async def read(self, path: str) -> str:
        """
        Read file contents.
        
        Args:
            path: File path
            
        Returns:
            File contents as string
        """
        if not self.client.rpc:
            return ""
        return await self.client.rpc.storage_read(path)
    
    async def write(self, path: str, content: str) -> bool:
        """
        Write file contents.
        
        Args:
            path: File path
            content: Content to write
            
        Returns:
            True if successful
        """
        # Stub: In real implementation, would use Flipper RPC protocol
        return True
    
    async def delete(self, path: str) -> bool:
        """
        Delete file.
        
        Args:
            path: File path
            
        Returns:
            True if successful
        """
        # Stub: In real implementation, would use Flipper RPC protocol
        return True
    
    async def mkdir(self, path: str) -> bool:
        """
        Create directory.
        
        Args:
            path: Directory path
            
        Returns:
            True if successful
        """
        # Stub: In real implementation, would use Flipper RPC protocol
        return True


class FlipperApp:
    """
    Application launcher wrapper.
    
    Provides app launching and control on Flipper Zero.
    """
    
    def __init__(self, client: 'FlipperClient'):
        self.client = client
    
    async def launch(self, app_name: str, args: Optional[str] = None) -> bool:
        """
        Launch an application.
        
        Args:
            app_name: Application name (e.g., "BadUsb")
            args: Optional arguments
            
        Returns:
            True if launch successful
        """
        # Stub: In real implementation, would use Flipper RPC protocol
        return True
    
    async def stop(self, app_name: str) -> bool:
        """
        Stop a running application.
        
        Args:
            app_name: Application name
            
        Returns:
            True if stop successful
        """
        # Stub: In real implementation, would use Flipper RPC protocol
        return True


class FlipperClient:
    """
    High-level Flipper Zero RPC client.
    
    Provides a simplified interface to Flipper Zero operations,
    abstracting away the underlying protobuf RPC protocol.
    
    This is a stub implementation that would normally communicate
    with Flipper Zero using the official protobuf RPC protocol.
    """
    
    def __init__(self, transport: FlipperTransport):
        """
        Initialize Flipper client.
        
        Args:
            transport: Transport layer for communication
        """
        self.transport = transport
        self.connected = False
        self.rpc: Optional[FlipperRPC] = None
        
        # Sub-clients
        self.storage = FlipperStorage(self)
        self.app = FlipperApp(self)
    
    async def connect(self) -> bool:
        """
        Connect to Flipper Zero.
        
        Returns:
            True if connection successful
        """
        if not await self.transport.connect():
            return False
        
        # Initialize RPC client
        self.rpc = FlipperRPC(self.transport)
        
        # Test connection with ping
        try:
            # Give device a moment to initialize
            import asyncio
            await asyncio.sleep(0.5)
            
            # Try to ping (optional - may not work with all firmware versions)
            # If ping fails, we still consider connected if transport is connected
            await self.rpc.ping()
        except Exception:
            # Ping failed, but transport is connected - continue anyway
            pass
        
        self.connected = True
        return True
    
    async def disconnect(self) -> None:
        """Disconnect from Flipper Zero."""
        await self.transport.disconnect()
        self.connected = False
    
    async def get_firmware_version(self) -> str:
        """
        Get Flipper firmware version.
        
        Returns:
            Firmware version string
        """
        if self.rpc:
            try:
                info = await self.rpc.get_device_info()
                return info.get("firmware", "Unknown")
            except Exception:
                pass
        return "Unknown"
    
    async def get_device_info(self) -> dict[str, Any]:
        """
        Get device information.
        
        Returns:
            Device info dict
        """
        if self.rpc:
            try:
                return await self.rpc.get_device_info()
            except Exception:
                pass
        
        # Fallback
        return {
            "name": "Flipper Zero",
            "hardware": "Flipper Zero",
            "firmware": await self.get_firmware_version()
        }
    
    async def send_rpc(self, command: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Send RPC command to Flipper.
        
        Args:
            command: RPC command name
            params: Command parameters
            
        Returns:
            RPC response
        """
        # Stub: Would normally encode to protobuf and send via transport
        return {"status": "ok"}
