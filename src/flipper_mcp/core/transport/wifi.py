"""WiFi transport for Flipper Zero (ESP32 WiFi Dev Board)."""

import asyncio
from typing import Optional

from .base import FlipperTransport


class WiFiTransport(FlipperTransport):
    """
    WiFi transport implementation for ESP32 WiFi Dev Board.
    
    Connects to Flipper Zero via network socket.
    """
    
    def __init__(self, config: dict):
        """
        Initialize WiFi transport.
        
        Args:
            config: WiFi configuration with 'host' and 'port'
        """
        super().__init__(config)
        self.host = config.get("host", "192.168.1.1")
        self.port = config.get("port", 8080)
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
    
    async def connect(self) -> bool:
        """
        Connect to Flipper Zero via WiFi.
        
        Returns:
            True if connection successful
        """
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.host, self.port
            )
            self.connected = True
            return True
        except (OSError, asyncio.TimeoutError) as e:
            print(f"WiFi connection failed: {e}")
            self.connected = False
            return False
    
    async def disconnect(self) -> None:
        """Close WiFi connection."""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        self.connected = False
    
    async def send(self, data: bytes) -> None:
        """
        Send data over WiFi.
        
        Args:
            data: Bytes to send
        """
        if not self.writer:
            raise RuntimeError("WiFi not connected")
        
        self.writer.write(data)
        await self.writer.drain()
    
    async def receive(self, timeout: Optional[float] = None) -> bytes:
        """
        Receive data from WiFi.
        
        Args:
            timeout: Optional timeout in seconds
            
        Returns:
            Received bytes
        """
        if not self.reader:
            raise RuntimeError("WiFi not connected")
        
        try:
            if timeout:
                data = await asyncio.wait_for(
                    self.reader.read(4096),
                    timeout=timeout
                )
            else:
                data = await self.reader.read(4096)
            return data
        except asyncio.TimeoutError:
            return b""
    
    async def is_connected(self) -> bool:
        """
        Check if WiFi is connected.
        
        Returns:
            True if connected
        """
        return self.connected and self.writer is not None and not self.writer.is_closing()
