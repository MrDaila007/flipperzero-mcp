"""USB Serial transport for Flipper Zero."""

import asyncio
from typing import Optional
import serial
import serial.tools.list_ports

from .base import FlipperTransport


class USBTransport(FlipperTransport):
    """
    USB Serial transport implementation.
    
    Connects to Flipper Zero via USB serial port.
    """
    
    def __init__(self, config: dict):
        """
        Initialize USB transport.
        
        Args:
            config: USB configuration with 'port' and 'baudrate'
        """
        super().__init__(config)
        self.port = config.get("port", self._auto_detect_port())
        self.baudrate = config.get("baudrate", 115200)
        self.timeout = config.get("timeout", 1.0)
        self.serial: Optional[serial.Serial] = None
    
    def _auto_detect_port(self) -> str:
        """
        Auto-detect Flipper Zero USB port.
        
        Returns:
            Port path or default
        """
        # Look for Flipper Zero USB device
        ports = serial.tools.list_ports.comports()
        for port in ports:
            # Flipper Zero VID:PID or description match
            if "Flipper" in str(port.description) or \
               (port.vid == 0x0483 and port.pid == 0x5740):  # STM32 VID:PID
                return port.device
        
        # Default fallback
        return "/dev/ttyACM0"
    
    async def connect(self) -> bool:
        """
        Connect to Flipper Zero via USB.
        
        Returns:
            True if connection successful
        """
        try:
            # Open serial port
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            
            # Wait for connection to stabilize
            await asyncio.sleep(0.5)
            
            self.connected = True
            return True
            
        except (serial.SerialException, OSError) as e:
            print(f"USB connection failed: {e}")
            self.connected = False
            return False
    
    async def disconnect(self) -> None:
        """Close USB connection."""
        if self.serial and self.serial.is_open:
            self.serial.close()
        self.connected = False
    
    async def send(self, data: bytes) -> None:
        """
        Send data over USB.
        
        Args:
            data: Bytes to send
        """
        if not self.serial or not self.serial.is_open:
            raise RuntimeError("USB not connected")
        
        # Run serial write in executor to avoid blocking
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.serial.write, data)
    
    async def receive(self, timeout: Optional[float] = None) -> bytes:
        """
        Receive data from USB.
        
        Args:
            timeout: Optional timeout in seconds
            
        Returns:
            Received bytes
        """
        if not self.serial or not self.serial.is_open:
            raise RuntimeError("USB not connected")
        
        # Use provided timeout or default
        old_timeout = self.serial.timeout
        if timeout is not None:
            self.serial.timeout = timeout
        
        try:
            # Run serial read in executor
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                self.serial.read,
                4096  # Max bytes to read
            )
            return data
        finally:
            self.serial.timeout = old_timeout
    
    async def is_connected(self) -> bool:
        """
        Check if USB is connected.
        
        Returns:
            True if connected
        """
        return self.connected and self.serial is not None and self.serial.is_open
