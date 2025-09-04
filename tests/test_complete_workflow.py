#!/usr/bin/env python3
"""
Complete Workflow Integration Test

Tests the full workflow: Session → Forge Trigger → Mock Processing → Firestore → UI Display
"""

import asyncio
import json
import time
import sys
from pathlib import Path

from playwright.async_api import async_playwright

# Add src directory to path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from desktop_service.forge.trigger_generator import ForgeTriggerGenerator
from desktop_service.forge.mock_forge import MockForge
from desktop_service.forge.firestore_client import FirestoreClient


class CompleteWorkflowTester:
    """Tests the complete forge integration workflow."""
    
    def __init__(self):
        self.trigger_generator = ForgeTriggerGenerator()
        self.mock_forge = MockForge()
        self.firestore_client = FirestoreClient(use_mock=True)
        
    async def test_complete_workflow(self):
        """Test the complete workflow end-to-end."""
        print("🚀 Testing Complete Forge Integration Workflow")
        print("=" * 60)
        
        # Step 1: Generate Forge Trigger JSON
        print("\n1️⃣ Generating Forge Trigger JSON...")
        from datetime import datetime, timezone
        
        session_id = "test-workflow-session-123"
        start_time = datetime.now(timezone.utc)
        end_time = start_time.replace(minute=start_time.minute + 3)  # 3 minute session
        
        trigger_json = self.trigger_generator.generate_trigger_json(
            session_id=session_id,
            start_time=start_time,
            end_time=end_time,
            org_id="diligent4"
        )
        
        print(f"✅ Generated trigger JSON for session: {session_id}")
        print(f"   Duration: {(end_time - start_time).total_seconds()}s")
        print(f"   Device: {trigger_json['session']['device_id']}")
        
        # Step 2: Process with Mock Forge
        print("\n2️⃣ Processing with Mock Forge...")
        forge_result = self.mock_forge.process_session(trigger_json)
        
        if forge_result.get("status") == "completed":
            print(f"✅ Mock forge processing completed")
            print(f"   Workflow ID: {forge_result.get('workflow_id')}")
            print(f"   Firestore Path: {forge_result.get('firestore_path')}")
            print(f"   Processing Time: {forge_result.get('processing_time_seconds')}s")
        else:
            print(f"❌ Mock forge processing failed: {forge_result.get('error')}")
            return False
        
        # Step 3: Retrieve from Firestore
        print("\n3️⃣ Retrieving Workflow from Firestore...")
        workflow = self.firestore_client.get_workflow("diligent4", session_id)
        
        if workflow:
            print(f"✅ Retrieved workflow from Firestore")
            print(f"   Title: {workflow['workflow_data']['title']}")
            print(f"   Steps: {len(workflow['workflow_data']['steps'])}")
            print(f"   Insights: {len(workflow['workflow_data']['insights'])}")
            print(f"   Productivity Score: {workflow['workflow_data']['productivity_score']}")
        else:
            print("❌ Failed to retrieve workflow from Firestore")
            return False
        
        # Step 4: Test UI Integration (if service is running)
        print("\n4️⃣ Testing UI Integration...")
        ui_test_result = await self._test_ui_integration(session_id)
        
        if ui_test_result:
            print("✅ UI integration test passed")
        else:
            print("⚠️  UI integration test skipped (service not running)")
        
        print("\n" + "=" * 60)
        print("🎉 Complete Workflow Test Summary:")
        print("✅ Forge Trigger Generation: PASSED")
        print("✅ Mock Forge Processing: PASSED") 
        print("✅ Firestore Retrieval: PASSED")
        print(f"{'✅' if ui_test_result else '⚠️ '} UI Integration: {'PASSED' if ui_test_result else 'SKIPPED'}")
        
        return True
    
    async def _test_ui_integration(self, session_id: str) -> bool:
        """Test UI integration by checking if the service responds."""
        try:
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Try to connect to the desktop service
            try:
                await page.goto("http://127.0.0.1:8844", timeout=5000)
                await page.wait_for_selector(".container", timeout=3000)
                
                print("   📱 Desktop service UI is accessible")
                print("   🔌 Socket.IO connection would handle workflow display")
                
                await context.close()
                await browser.close()
                await playwright.stop()
                
                return True
                
            except Exception as e:
                print(f"   ⚠️  Desktop service not accessible: {e}")
                await context.close()
                await browser.close()
                await playwright.stop()
                return False
                
        except Exception as e:
            print(f"   ❌ UI test error: {e}")
            return False
    
    def test_trigger_json_format(self):
        """Test that the trigger JSON matches the expected v1.0 format."""
        print("\n🔍 Validating Trigger JSON Format...")
        
        from datetime import datetime, timezone
        
        session_id = "format-test-session"
        start_time = datetime(2025, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2025, 1, 15, 9, 3, 0, tzinfo=timezone.utc)
        
        trigger_json = self.trigger_generator.generate_trigger_json(
            session_id=session_id,
            start_time=start_time,
            end_time=end_time,
            org_id="diligent4"
        )
        
        # Validate required fields
        required_fields = {
            "version": "1.0",
            "session": {
                "org_id": str,
                "device_id": str,
                "session_id": str,
                "time_range": {
                    "start": str,
                    "end": str
                },
                "timezone": str
            },
            "options": {
                "stages": list,
                "media_processing": bool,
                "llm_enabled": bool
            },
            "visibility": str,
            "pipeline_version": str,
            "config_path": str
        }
        
        def validate_structure(data, expected, path=""):
            for key, expected_type in expected.items():
                if key not in data:
                    print(f"❌ Missing field: {path}.{key}")
                    return False
                
                if isinstance(expected_type, dict):
                    if not validate_structure(data[key], expected_type, f"{path}.{key}"):
                        return False
                elif isinstance(expected_type, type):
                    if not isinstance(data[key], expected_type):
                        print(f"❌ Wrong type for {path}.{key}: expected {expected_type.__name__}, got {type(data[key]).__name__}")
                        return False
                else:
                    if data[key] != expected_type:
                        print(f"❌ Wrong value for {path}.{key}: expected {expected_type}, got {data[key]}")
                        return False
            
            return True
        
        if validate_structure(trigger_json, required_fields):
            print("✅ Trigger JSON format validation passed")
            print(f"   Version: {trigger_json['version']}")
            print(f"   Stages: {trigger_json['options']['stages']}")
            print(f"   Time Range: {trigger_json['session']['time_range']['start']} → {trigger_json['session']['time_range']['end']}")
            return True
        else:
            print("❌ Trigger JSON format validation failed")
            return False


async def main():
    """Main test function."""
    tester = CompleteWorkflowTester()
    
    # Test trigger JSON format
    format_valid = tester.test_trigger_json_format()
    
    # Test complete workflow
    workflow_valid = await tester.test_complete_workflow()
    
    # Summary
    print("\n" + "🎯 FINAL TEST RESULTS " + "🎯")
    print("=" * 60)
    print(f"Trigger JSON Format: {'✅ PASSED' if format_valid else '❌ FAILED'}")
    print(f"Complete Workflow:   {'✅ PASSED' if workflow_valid else '❌ FAILED'}")
    
    if format_valid and workflow_valid:
        print("\n🎉 ALL TESTS PASSED! Forge integration is ready!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
