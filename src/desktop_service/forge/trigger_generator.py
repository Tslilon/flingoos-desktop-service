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
                            org_id: Optional[str] = None, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate Forge Trigger v1.0 JSON.
        
        Args:
            session_id: Unique session identifier
            start_time: Session start time
            end_time: Session end time
            org_id: Organization ID (auto-detected from Bridge if None)
            device_id: Device ID (auto-detected from Bridge if None)
            
        Returns:
            Forge trigger JSON dictionary
        """
        try:
            # Get device_id and org_id from bridge if not provided
            if not device_id or not org_id:
                bridge_info = self._get_bridge_info()
                if not bridge_info:
                    raise ValueError(
                        "Could not retrieve device_id and org_id from Bridge. "
                        "Ensure Bridge is running and properly configured. "
                        "Fallback generation is disabled to prevent data location mismatches."
                    )
                
                if not device_id:
                    device_id = bridge_info.get("device_id")
                    if not device_id:
                        raise ValueError("Bridge response missing device_id field")
                
                if not org_id:
                    org_id = bridge_info.get("org_id")
                    if not org_id:
                        raise ValueError("Bridge response missing org_id field")
            
            # Format timestamps in RFC3339 UTC format with Z suffix (millisecond precision)
            # The input times are in local timezone (Asia/Jerusalem), convert to UTC
            import zoneinfo
            BRIDGE_TZ = "Asia/Jerusalem"
            local_tz = zoneinfo.ZoneInfo(BRIDGE_TZ)
            
            # Assume input times are in local timezone, convert to UTC
            if start_time.tzinfo is None:
                start_local = start_time.replace(tzinfo=local_tz)
            else:
                start_local = start_time.astimezone(local_tz)
            
            if end_time.tzinfo is None:
                end_local = end_time.replace(tzinfo=local_tz)
            else:
                end_local = end_time.astimezone(local_tz)
            
            # Convert to UTC
            start_utc = start_local.astimezone(timezone.utc)
            end_utc = end_local.astimezone(timezone.utc)
            
            # Convert to millisecond precision and use Z suffix
            start_iso = start_utc.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            end_iso = end_utc.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            
            # Generate trigger JSON (matching GOOD format)
            trigger_json = {
                "pipeline_version": "   1.0",
                "config_path": "secrets/config.toml",
                "session": {
                    "org_id": org_id,
                    "device_id": device_id,
                    "time_range": {
                        "start": start_iso,
                        "end": end_iso
                    },
                    "timezone": BRIDGE_TZ
                },
                "options": {
                    "stages": ["A", "B", "C", "D", "E", "F", "U"],
                    "media_processing": True,
                    "llm_enabled": True,
                    "include_flowchart": True
                },
                "visibility": "private"
            }

            # trigger_json = {
            #     "pipeline_version": "1.0",
            #     "config_path": "secrets/config.toml",
            #     "session": {
            #         "org_id": "diligent4",
            #         "device_id": "DESKTOP-OBMAPKG-40770579",
            #         "time_range": {
            #         "start": "2025-08-21T13:08:09Z",
            #         "end": "2025-08-21T13:09:15.066Z"
            #         },
            #         "timezone": "Asia/Jerusalem"
            #     },
            #     "options": {
            #         "stages": ["A", "B", "C", "D", "E", "F", "U"],
            #         "media_processing": True,
            #         "llm_enabled": True,
            #         "include_flowchart": True
            #     },
            #     "visibility": "private"
            # }
            
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
    
    def _get_bridge_info(self) -> Optional[Dict[str, str]]:
        """Get device_id and org_id from bridge service status response."""
        try:
            status_response = self.command_client.get_status()
            if status_response.get("success") and "data" in status_response:
                data = status_response["data"]
                device_id = data.get("device_id")
                org_id = data.get("org_id")
                
                if device_id and org_id:
                    logger.info(f"Retrieved from Bridge - device_id: {device_id}, org_id: {org_id}")
                    return {"device_id": device_id, "org_id": org_id}
                else:
                    missing = []
                    if not device_id:
                        missing.append("device_id")
                    if not org_id:
                        missing.append("org_id")
                    logger.warning(f"Bridge status response missing fields: {', '.join(missing)}")
            else:
                logger.warning(f"Bridge status request failed: {status_response}")
            return None
        except Exception as e:
            logger.error(f"Error getting bridge info: {e}")
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
