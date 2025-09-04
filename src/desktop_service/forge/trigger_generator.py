"""
Forge Trigger JSON Generator

Creates the Trigger v1.0 JSON format that forge expects for processing sessions.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pathlib import Path

from ..bridge_client.command_client import CommandClient

logger = logging.getLogger(__name__)


class ForgeTriggerGenerator:
    """Generates Forge Trigger v1.0 JSON files for session processing."""
    
    def __init__(self):
        self.command_client = CommandClient()
    
    def generate_trigger_json(self, session_id: str, start_time: datetime, end_time: datetime, 
                            org_id: str = "diligent4", device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate Forge Trigger v1.0 JSON.
        
        Args:
            session_id: Unique session identifier
            start_time: Session start time
            end_time: Session end time
            org_id: Organization ID (default: diligent4)
            device_id: Device ID (auto-detected if None)
            
        Returns:
            Forge trigger JSON dictionary
        """
        try:
            # Get device ID from bridge if not provided
            if not device_id:
                try:
                    status_response = self.command_client.get_status()
                    # Try to extract device ID from bridge status or use fallback
                    device_id = self._get_device_id_from_bridge() or self._generate_fallback_device_id()
                except Exception as e:
                    logger.warning(f"Could not get device ID from bridge: {e}")
                    device_id = self._generate_fallback_device_id()
            
            # Format timestamps in ISO format with timezone
            start_iso = start_time.replace(tzinfo=timezone.utc).isoformat()
            end_iso = end_time.replace(tzinfo=timezone.utc).isoformat()
            
            # Generate trigger JSON
            trigger_json = {
                "version": "1.0",
                "session": {
                    "org_id": org_id,
                    "device_id": device_id,
                    "session_id": session_id,  # Add session ID for tracking
                    "time_range": {
                        "start": start_iso,
                        "end": end_iso
                    },
                    "timezone": "UTC"  # Using UTC for consistency
                },
                "options": {
                    "stages": ["A", "B", "C", "D", "E", "F"],
                    "media_processing": True,
                    "llm_enabled": True
                },
                "visibility": "private",
                "pipeline_version": "0.1.0",
                "config_path": "secrets/config.toml"
            }
            
            logger.info(f"Generated forge trigger for session {session_id}: "
                       f"device={device_id}, duration={int((end_time - start_time).total_seconds())}s")
            
            return trigger_json
            
        except Exception as e:
            logger.error(f"Error generating forge trigger JSON: {e}")
            raise
    
    def save_trigger_to_file(self, trigger_json: Dict[str, Any], output_path: str) -> bool:
        """
        Save trigger JSON to file.
        
        Args:
            trigger_json: Trigger JSON dictionary
            output_path: File path to save JSON
            
        Returns:
            True if successful, False otherwise
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w') as f:
                json.dump(trigger_json, f, indent=2)
            
            logger.info(f"Saved forge trigger JSON to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving trigger JSON to {output_path}: {e}")
            return False
    
    def _get_device_id_from_bridge(self) -> Optional[str]:
        """Try to get device ID from bridge service."""
        try:
            # This would need to be implemented in the bridge API
            # For now, return None to use fallback
            return None
        except Exception:
            return None
    
    def _generate_fallback_device_id(self) -> str:
        """Generate a fallback device ID."""
        import platform
        import hashlib
        
        # Create a simple device ID based on hostname and platform
        hostname = platform.node()
        system_info = f"{platform.system()}-{platform.machine()}"
        
        # Create a short hash for uniqueness
        hash_input = f"{hostname}-{system_info}".encode()
        device_hash = hashlib.md5(hash_input).hexdigest()[:8]
        
        return f"{hostname}-{device_hash}"
