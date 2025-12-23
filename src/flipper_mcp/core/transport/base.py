"""Transport layer abstraction for Flipper Zero communication."""

from abc import ABC, abstractmethod
from typing import Optional


class FlipperTransport(ABC):
    """
    Abstract base class for Flipper Zero transport implementations.
    
    Provides a common interface for different connection methods:
    - USB Serial
    - WiFi (ESP32)
    - Bluetooth LE
    """
    
    def __init__(self, config: dict):
        """
        Initialize transport with configuration.
        
        Args:
            config: Transport-specific configuration
        """
        self.config = config
        self.connected = False
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to Flipper Zero.
        
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to Flipper Zero."""
        pass
    
    @abstractmethod
    async def send(self, data: bytes) -> None:
        """
        Send data to Flipper Zero.
        
        Args:
            data: Raw bytes to send
        """
        pass
    
    @abstractmethod
    async def receive(self, timeout: Optional[float] = None) -> bytes:
        """
        Receive data from Flipper Zero.
        
        Args:
            timeout: Optional timeout in seconds
            
        Returns:
            Received bytes
        """
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """
        Check if transport is connected.
        
        Returns:
            True if connected, False otherwise
        """
        pass
    
    def get_name(self) -> str:
        """
        Get transport name for logging.
        
        Returns:
            Transport name (e.g., "USB", "WiFi", "BLE")
        """
        return self.__class__.__name__.replace("Transport", "")
