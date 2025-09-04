"""
Mock Forge Command

Simulates the forge processing pipeline for testing and development.
Creates mock workflows and uploads them to Firestore.
"""

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class MockForge:
    """Mock forge processor that simulates workflow generation."""
    
    def __init__(self):
        self.processing_time = 5  # Simulate 5 seconds processing time
    
    def process_session(self, trigger_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a session trigger and return completion response.
        
        Args:
            trigger_json: Forge trigger JSON
            
        Returns:
            Processing completion response
        """
        try:
            session_info = trigger_json.get("session", {})
            session_id = session_info.get("session_id", str(uuid.uuid4()))
            org_id = session_info.get("org_id", "diligent4")
            device_id = session_info.get("device_id", "unknown-device")
            
            logger.info(f"Mock forge processing session {session_id} for {org_id}/{device_id}")
            
            # Simulate processing time
            time.sleep(self.processing_time)
            
            # Generate mock workflow
            workflow = self._generate_mock_workflow(trigger_json)
            
            # Simulate uploading to Firestore
            firestore_path = f"organizations/{org_id}/workflows/{session_id}"
            self._mock_upload_to_firestore(firestore_path, workflow)
            
            # Return completion response
            response = {
                "status": "completed",
                "session_id": session_id,
                "processing_time_seconds": self.processing_time,
                "firestore_path": firestore_path,
                "workflow_id": workflow["workflow_id"],
                "message": "Session processed successfully",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Mock forge completed processing {session_id}: {firestore_path}")
            return response
            
        except Exception as e:
            logger.error(f"Mock forge processing error: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def _generate_mock_workflow(self, trigger_json: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a mock workflow result."""
        session_info = trigger_json.get("session", {})
        session_id = session_info.get("session_id", str(uuid.uuid4()))
        
        # Create realistic mock workflow data
        workflow = {
            "workflow_id": str(uuid.uuid4()),
            "session_id": session_id,
            "org_id": session_info.get("org_id", "diligent4"),
            "device_id": session_info.get("device_id", "unknown-device"),
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "pipeline_version": trigger_json.get("pipeline_version", "0.1.0"),
            "status": "completed",
            
            # Mock workflow stages
            "stages": {
                "A": {
                    "name": "Data Segmentation",
                    "status": "completed",
                    "duration_ms": 1200,
                    "segments_created": 15
                },
                "B": {
                    "name": "Activity Detection",
                    "status": "completed", 
                    "duration_ms": 800,
                    "activities_detected": 8
                },
                "C": {
                    "name": "Audio Transcription",
                    "status": "completed",
                    "duration_ms": 2100,
                    "words_transcribed": 247
                },
                "D": {
                    "name": "Context Analysis",
                    "status": "completed",
                    "duration_ms": 1500,
                    "contexts_identified": 5
                },
                "E": {
                    "name": "LLM Processing",
                    "status": "completed",
                    "duration_ms": 3200,
                    "insights_generated": 12
                },
                "F": {
                    "name": "Workflow Generation",
                    "status": "completed",
                    "duration_ms": 900,
                    "workflow_steps": 6
                }
            },
            
            # Mock workflow results
            "workflow_data": {
                "title": "Data Analysis Session",
                "summary": "User performed data analysis tasks including spreadsheet work, research, and documentation.",
                "duration_seconds": int((datetime.fromisoformat(session_info.get("time_range", {}).get("end", "2025-01-01T00:01:00+00:00").replace("Z", "+00:00")) - 
                                       datetime.fromisoformat(session_info.get("time_range", {}).get("start", "2025-01-01T00:00:00+00:00").replace("Z", "+00:00"))).total_seconds()),
                "steps": [
                    {
                        "step": 1,
                        "action": "Opened spreadsheet application",
                        "timestamp": "00:00:05",
                        "confidence": 0.95,
                        "context": "productivity"
                    },
                    {
                        "step": 2,
                        "action": "Loaded data file with customer information",
                        "timestamp": "00:00:12",
                        "confidence": 0.88,
                        "context": "data_analysis"
                    },
                    {
                        "step": 3,
                        "action": "Applied filters to identify high-value customers",
                        "timestamp": "00:00:45",
                        "confidence": 0.92,
                        "context": "data_analysis"
                    },
                    {
                        "step": 4,
                        "action": "Created pivot table for revenue analysis",
                        "timestamp": "00:01:20",
                        "confidence": 0.89,
                        "context": "data_analysis"
                    },
                    {
                        "step": 5,
                        "action": "Generated charts for presentation",
                        "timestamp": "00:02:10",
                        "confidence": 0.91,
                        "context": "visualization"
                    },
                    {
                        "step": 6,
                        "action": "Saved analysis results to shared folder",
                        "timestamp": "00:02:45",
                        "confidence": 0.94,
                        "context": "collaboration"
                    }
                ],
                "insights": [
                    "User demonstrated strong analytical skills",
                    "Efficient use of spreadsheet features",
                    "Focus on data-driven decision making",
                    "Good documentation practices"
                ],
                "categories": ["data_analysis", "productivity", "business_intelligence"],
                "productivity_score": 0.87
            },
            
            # Processing metadata
            "processing_metadata": {
                "total_processing_time_ms": 9700,
                "data_sources": ["mouse_events", "keyboard_events", "window_changes", "audio"],
                "files_processed": 12,
                "total_events": 1247
            }
        }
        
        return workflow
    
    def _mock_upload_to_firestore(self, firestore_path: str, workflow: Dict[str, Any]):
        """Mock uploading workflow to Firestore."""
        # In a real implementation, this would upload to Firestore
        # For now, we'll save to a local file to simulate the process
        
        # Create mock firestore directory structure
        mock_firestore_dir = Path("mock_firestore") / firestore_path
        mock_firestore_dir.mkdir(parents=True, exist_ok=True)
        
        # Save workflow as JSON
        workflow_file = mock_firestore_dir / "workflow.json"
        with open(workflow_file, 'w') as f:
            json.dump(workflow, f, indent=2)
        
        logger.info(f"Mock uploaded workflow to {firestore_path} (saved locally to {workflow_file})")


def main():
    """Main function for testing mock forge."""
    # Example trigger JSON
    trigger_json = {
        "version": "1.0",
        "session": {
            "org_id": "diligent4",
            "device_id": "DESKTOP-TEST-12345678",
            "session_id": "test-session-123",
            "time_range": {
                "start": "2025-01-15T09:00:00.000+00:00",
                "end": "2025-01-15T09:03:00.000+00:00"
            },
            "timezone": "UTC"
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
    
    # Test mock forge
    forge = MockForge()
    result = forge.process_session(trigger_json)
    
    print("Mock Forge Result:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
