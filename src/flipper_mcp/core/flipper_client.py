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
        
        # SD card status cache
        self._sd_card_available: Optional[bool] = None
    
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
                # Try multiple possible keys for firmware version
                fw = (info.get("firmware") or 
                      info.get("firmware_version") or 
                      info.get("version") or 
                      "Unknown")
                if fw and fw != "Unknown" and "not fully implemented" not in fw:
                    return fw
            except Exception:
                pass
        return "Unknown"
    
    async def get_device_info(self) -> dict[str, Any]:
        """
        Get device information.
        
        Returns comprehensive device information including:
        - name: Device name
        - hardware: Hardware model/version
        - firmware: Firmware version
        - firmware_version: Detailed firmware version
        - hardware_model: Hardware model
        - hardware_version: Hardware version
        - serial_number: Device serial number (if available)
        
        Returns:
            Device info dict with all available information
        """
        if self.rpc:
            try:
                info = await self.rpc.get_device_info()
                # Ensure we have at least basic structure
                if info and isinstance(info, dict):
                    # Normalize keys
                    normalized = {
                        "name": info.get("name") or info.get("device_name") or "Flipper Zero",
                        "hardware": (info.get("hardware") or 
                                   info.get("hardware_model") or 
                                   info.get("model") or 
                                   "Flipper Zero"),
                        "firmware": (info.get("firmware") or 
                                   info.get("firmware_version") or 
                                   info.get("version") or 
                                   "Unknown"),
                    }
                    
                    # Add additional fields if available
                    if info.get("firmware_version"):
                        normalized["firmware_version"] = info["firmware_version"]
                    if info.get("hardware_model"):
                        normalized["hardware_model"] = info["hardware_model"]
                    if info.get("hardware_version"):
                        normalized["hardware_version"] = info["hardware_version"]
                    if info.get("serial_number") or info.get("serial"):
                        normalized["serial_number"] = info.get("serial_number") or info.get("serial")
                    
                    return normalized
            except Exception as e:
                # Log error but continue to fallback
                pass
        
        # Fallback with basic info
        fw_version = await self.get_firmware_version()
        return {
            "name": "Flipper Zero",
            "hardware": "Flipper Zero",
            "firmware": fw_version if fw_version != "Unknown" else "Unknown (RPC protocol not fully implemented)"
        }
    
    async def check_sd_card_available(self, force_check: bool = False) -> bool:
        """
        Check if MicroSD card is available and accessible.
        
        Detection method: Try to write a test file to /ext directory (SD card mount point),
        then delete it. If both operations succeed, SD card is present and writable.
        This is more reliable than just listing, as listing may succeed even without SD card.
        
        The result is cached to avoid repeated checks. Use force_check=True
        to bypass the cache and check again.
        
        Args:
            force_check: If True, bypass cache and check again
            
        Returns:
            True if SD card is available, False otherwise
        """
        # Return cached result if available and not forcing a check
        if not force_check and self._sd_card_available is not None:
            return self._sd_card_available
        
        # If not connected, SD card cannot be available
        if not self.connected:
            self._sd_card_available = False
            return False
        
        # Test SD card by trying to write and delete a test file
        # This is more reliable than just listing, as listing may return empty
        # even when SD card is not present
        test_file_path = "/ext/.sd_card_test"
        test_content = "sd_card_test"
        
        try:
            # Try to write a test file
            write_success = await self.storage.write(test_file_path, test_content)
            if not write_success:
                # Write failed - SD card not available
                self._sd_card_available = False
                return False
            
            # Try to read it back to verify it was actually written
            # (some stub implementations might return True without actually writing)
            try:
                read_content = await self.storage.read(test_file_path)
                if read_content != test_content:
                    # Content doesn't match - write didn't actually work
                    self._sd_card_available = False
                    return False
            except Exception:
                # Can't read it back - write didn't actually work
                self._sd_card_available = False
                return False
            
            # Try to delete the test file
            try:
                await self.storage.delete(test_file_path)
            except Exception:
                # Deletion failed, but that's okay - we verified write worked
                pass
            
            # All checks passed - SD card is available
            self._sd_card_available = True
            return True
            
        except Exception:
            # Any error during write/read/delete means SD card is not available
            self._sd_card_available = False
            return False
    
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
