"""Flipper Zero Protobuf RPC implementation.

This module implements the Flipper Zero RPC protocol using Protocol Buffers
based on the official protobuf schemas from:
https://github.com/flipperdevices/flipperzero-protobuf

Uses generated protobuf code from proto/ directory.
"""

import struct
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from .transport.base import FlipperTransport

# Import generated protobuf classes
try:
    from .protobuf_gen import flipper_pb2, system_pb2, property_pb2
    PROTOBUF_AVAILABLE = True
except ImportError:
    PROTOBUF_AVAILABLE = False
    if TYPE_CHECKING:
        # For type checking only
        from .protobuf_gen import flipper_pb2, system_pb2, property_pb2
    else:
        flipper_pb2 = None
        system_pb2 = None
        property_pb2 = None


class ProtobufRPC:
    """
    Flipper Zero Protobuf RPC client.
    
    Implements the RPC protocol using protobuf messages as defined in
    the flipperzero-protobuf repository.
    """
    
    def __init__(self, transport: FlipperTransport):
        """
        Initialize Protobuf RPC client.
        
        Args:
            transport: Transport layer for communication
        """
        if not PROTOBUF_AVAILABLE:
            raise ImportError("Protobuf generated code not available. Run 'protoc' to generate Python code from .proto files.")
        
        self.transport = transport
        self.command_id = 0
    
    def _get_next_command_id(self) -> int:
        """Get next command ID for RPC calls."""
        self.command_id = (self.command_id + 1) % 0xFFFFFFFF
        return self.command_id
    
    async def _send_rpc_message(
        self, 
        main_message: Any  # flipper_pb2.Main
    ) -> Optional[Any]:  # Optional[flipper_pb2.Main]
        """
        Send a protobuf RPC message and receive response.
        
        Flipper Zero RPC protocol:
        1. Send: [4 bytes: message_length][protobuf Main message]
        2. Receive: [4 bytes: response_length][protobuf Main message]
        
        Args:
            main_message: Main protobuf message to send
            
        Returns:
            Main response message or None
        """
        try:
            # Serialize Main message
            message_data = main_message.SerializeToString()
            
            # Prepend message length (4 bytes, big-endian)
            message = struct.pack('>I', len(message_data)) + message_data
            
            # Send message
            await self.transport.send(message)
            
            # Receive response with timeout
            # Read length (4 bytes) - use shorter timeout
            import asyncio
            try:
                length_bytes = await asyncio.wait_for(
                    self.transport.receive(timeout=2.0),
                    timeout=2.5
                )
            except (asyncio.TimeoutError, Exception):
                return None
            
            if not length_bytes or len(length_bytes) < 4:
                return None
            
            response_length = struct.unpack('>I', length_bytes[:4])[0]
            if response_length == 0 or response_length > 1000000:  # Sanity check
                return None
            
            # Read response data with timeout
            try:
                response = await asyncio.wait_for(
                    self.transport.receive(timeout=2.0),
                    timeout=2.5
                )
            except (asyncio.TimeoutError, Exception):
                return None
            
            if len(response) < (response_length - 4):
                # Need to read more
                try:
                    remaining = response_length - 4 - len(response)
                    additional = await asyncio.wait_for(
                        self.transport.receive(timeout=2.0),
                        timeout=2.5
                    )
                    response = response + additional
                except (asyncio.TimeoutError, Exception):
                    # Partial response - try to parse what we have
                    pass
            
            response_data = response[:(response_length - 4)] if len(response) >= (response_length - 4) else response
            
            if not response_data:
                return None
            
            # Parse Main message
            main_response = flipper_pb2.Main()
            main_response.ParseFromString(response_data)
            
            return main_response
            
        except Exception:
            return None
    
    async def get_device_info(self) -> Dict[str, Any]:
        """
        Get device information using system.get_device_info RPC.
        
        DeviceInfo returns multiple key-value pairs, so we need to
        collect all responses until has_next is false.
        
        Returns:
            Dictionary of device information key-value pairs
        """
        info = {}
        
        # Add overall timeout to prevent hanging
        import asyncio
        try:
            return await asyncio.wait_for(self._get_device_info_internal(), timeout=3.0)
        except (asyncio.TimeoutError, Exception):
            return info
    
    async def _get_device_info_internal(self) -> Dict[str, Any]:
        """Internal implementation of get_device_info."""
        info = {}
        
        try:
            # Build Main message with DeviceInfoRequest
            main_request = flipper_pb2.Main()
            main_request.command_id = self._get_next_command_id()
            main_request.command_status = flipper_pb2.CommandStatus.OK
            main_request.has_next = False
            main_request.system_device_info_request.CopyFrom(system_pb2.DeviceInfoRequest())
            
            # Send request and get response
            main_response = await self._send_rpc_message(main_request)
            
            if main_response and main_response.command_status == flipper_pb2.CommandStatus.OK:
                # Check if we have a DeviceInfoResponse
                if main_response.HasField('system_device_info_response'):
                    device_info = main_response.system_device_info_response
                    if device_info.key and device_info.value:
                        info[device_info.key] = device_info.value
                
                # Handle has_next flag - collect all key-value pairs
                # Note: DeviceInfo can return multiple responses
                # Limit to prevent infinite loops
                max_iterations = 100
                iteration = 0
                while main_response.has_next and iteration < max_iterations:
                    iteration += 1
                    try:
                        # Read next response with timeout
                        import asyncio
                        length_bytes = await asyncio.wait_for(
                            self.transport.receive(timeout=2.0),
                            timeout=2.5
                        )
                        if not length_bytes or len(length_bytes) < 4:
                            break
                        
                        response_length = struct.unpack('>I', length_bytes[:4])[0]
                        if response_length == 0 or response_length > 1000000:
                            break
                        
                        response = await asyncio.wait_for(
                            self.transport.receive(timeout=2.0),
                            timeout=2.5
                        )
                        if len(response) < (response_length - 4):
                            remaining = response_length - 4 - len(response)
                            additional = await asyncio.wait_for(
                                self.transport.receive(timeout=2.0),
                                timeout=2.5
                            )
                            response = response + additional
                        
                        response_data = response[:(response_length - 4)] if len(response) >= (response_length - 4) else response
                        
                        # Parse next Main message
                        main_response = flipper_pb2.Main()
                        main_response.ParseFromString(response_data)
                        
                        if main_response.HasField('system_device_info_response'):
                            device_info = main_response.system_device_info_response
                            if device_info.key and device_info.value:
                                info[device_info.key] = device_info.value
                        
                        if main_response.command_status != flipper_pb2.CommandStatus.OK:
                            break
                    except (asyncio.TimeoutError, Exception):
                        # Timeout or error reading next response - stop collecting
                        break
                
        except Exception:
            pass
        
        # If we didn't get info from DeviceInfo, try property.get for common keys
        if not info:
            property_keys = [
                'firmware_version',
                'hardware_model',
                'hardware_version',
                'serial_number',
                'firmware_build_date',
                'firmware_git_hash'
            ]
            
            for key in property_keys:
                try:
                    value = await self.get_property(key)
                    if value:
                        info[key] = value
                except Exception:
                    pass
        
        return info
    
    async def get_property(self, key: str) -> Optional[str]:
        """
        Get a property value using property.get RPC.
        
        Args:
            key: Property key
            
        Returns:
            Property value or None
        """
        # Add overall timeout to prevent hanging
        import asyncio
        try:
            return await asyncio.wait_for(self._get_property_internal(key), timeout=2.0)
        except (asyncio.TimeoutError, Exception):
            return None
    
    async def _get_property_internal(self, key: str) -> Optional[str]:
        """Internal implementation of get_property."""
        try:
            # Build Main message with Property.GetRequest
            main_request = flipper_pb2.Main()
            main_request.command_id = self._get_next_command_id()
            main_request.command_status = flipper_pb2.CommandStatus.OK
            main_request.has_next = False
            
            # Set property_get_request
            get_request = property_pb2.GetRequest()
            get_request.key = key
            main_request.property_get_request.CopyFrom(get_request)
            
            # Send request and get response
            main_response = await self._send_rpc_message(main_request)
            
            if main_response and main_response.command_status == flipper_pb2.CommandStatus.OK:
                if main_response.HasField('property_get_response'):
                    return main_response.property_get_response.value
            
        except Exception:
            pass
        
        return None
