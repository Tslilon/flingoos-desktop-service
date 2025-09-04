"""
Command Client - Connects to running bridge service to send commands.
Uses Unix sockets for reliable IPC communication.

Adapted from flingoos-bridge for independent desktop service operation.
"""

import json
import socket
import time
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class CommandClient:
    """
    Client for sending commands to the running bridge service.
    Uses Unix sockets for reliable inter-process communication.
    """
    
    def __init__(self, socket_path: Optional[str] = None, timeout: float = 5.0):
        """
        Initialize command client.
        
        Args:
            socket_path: Path to Unix socket file (defaults to /tmp/flingoos_bridge.sock)
            timeout: Connection timeout in seconds
        """
        self.socket_path = socket_path or "/tmp/flingoos_bridge.sock"
        self.timeout = timeout
    
    def send_command(self, command: str, **kwargs) -> Dict[str, Any]:
        """
        Send command to bridge service.
        
        Args:
            command: Command name
            **kwargs: Command arguments
            
        Returns:
            Response dictionary from server
            
        Raises:
            ConnectionError: If unable to connect to bridge service
            TimeoutError: If command times out
        """
        # Prepare command data
        command_data = {
            "command": command,
            "timestamp": time.time(),
            **kwargs
        }
        
        # Connect to server and send command
        try:
            client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client_socket.settimeout(self.timeout)
            
            try:
                client_socket.connect(self.socket_path)
                
                # Send command
                command_json = json.dumps(command_data) + '\n'
                client_socket.send(command_json.encode('utf-8'))
                
                # Receive response
                response_data = b""
                while True:
                    chunk = client_socket.recv(4096)
                    if not chunk:
                        break
                    response_data += chunk
                    
                    # Check if we have complete JSON response (ends with newline)
                    if response_data.endswith(b'\n'):
                        break
                
                if not response_data:
                    raise ConnectionError("No response from bridge service")
                
                # Parse response
                try:
                    response = json.loads(response_data.decode('utf-8').strip())
                    return response
                except json.JSONDecodeError as e:
                    raise ConnectionError(f"Invalid response from bridge service: {e}")
                    
            finally:
                client_socket.close()
                
        except socket.timeout:
            raise TimeoutError(f"Command timed out after {self.timeout} seconds")
        except socket.error as e:
            if "No such file or directory" in str(e) or "Connection refused" in str(e):
                raise ConnectionError(
                    "Bridge service is not running. Start it with: python3 -m bridge.main run"
                )
            else:
                raise ConnectionError(f"Failed to connect to bridge service: {e}")
    
    def ping(self) -> Dict[str, Any]:
        """Ping the bridge service."""
        return self.send_command("ping")
    
    def get_status(self) -> Dict[str, Any]:
        """Get bridge service status."""
        return self.send_command("status")
    
    def start_audio_recording(self) -> Dict[str, Any]:
        """Start audio recording session."""
        return self.send_command("audio_start")
    
    def stop_audio_recording(self) -> Dict[str, Any]:
        """Stop audio recording session."""
        return self.send_command("audio_stop")
    
    def get_collectors_status(self) -> Dict[str, Any]:
        """Get status of all collectors."""
        return self.send_command("collectors_status")
    
    def is_bridge_running(self) -> bool:
        """Check if bridge service is running and responsive."""
        try:
            response = self.ping()
            return response.get("success", False)
        except (ConnectionError, TimeoutError):
            return False
