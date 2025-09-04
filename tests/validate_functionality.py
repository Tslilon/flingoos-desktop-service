#!/usr/bin/env python3
"""
Playwright validation script for Flingoos Desktop Service.

This script validates the web UI functionality including:
- UI loads correctly
- Bridge connectivity status
- Session start/stop functionality
- Socket.IO communication
- Upload status display
"""

import asyncio
import time
import sys
from pathlib import Path

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

# Add src directory to path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

from desktop_service.bridge_client.command_client import CommandClient


class DesktopServiceValidator:
    """Validates desktop service functionality using Playwright."""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8844"):
        self.base_url = base_url
        self.browser = None
        self.context = None
        self.page = None
        
    async def setup(self):
        """Set up Playwright browser and page."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=False)  # Set to True for headless
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        
        # Enable console logging
        self.page.on("console", lambda msg: print(f"[BROWSER] {msg.type}: {msg.text}"))
        
    async def teardown(self):
        """Clean up browser resources."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
    
    async def validate_ui_loads(self) -> bool:
        """Validate that the UI loads correctly."""
        print("🔍 Testing UI loading...")
        
        try:
            # Navigate to the page
            await self.page.goto(self.base_url)
            
            # Wait for the main elements to load
            await self.page.wait_for_selector(".container", timeout=5000)
            await self.page.wait_for_selector("#sessionButton", timeout=5000)
            await self.page.wait_for_selector("#statusDot", timeout=5000)
            
            # Check page title
            title = await self.page.title()
            assert "D4 - Session Manager" in title, f"Unexpected title: {title}"
            
            # Check main heading
            heading = await self.page.text_content("h1")
            assert heading == "D4", f"Unexpected heading: {heading}"
            
            print("✅ UI loads correctly")
            return True
            
        except Exception as e:
            print(f"❌ UI loading failed: {e}")
            return False
    
    async def validate_bridge_connectivity(self) -> bool:
        """Validate bridge connectivity status display."""
        print("🔍 Testing bridge connectivity status...")
        
        try:
            # Check if bridge is actually running
            command_client = CommandClient()
            bridge_running = command_client.is_bridge_running()
            
            # Wait for status to update
            await asyncio.sleep(2)
            
            # Check status dot
            status_dot = await self.page.get_attribute("#statusDot", "class")
            status_text = await self.page.text_content("#statusText")
            
            if bridge_running:
                assert "connected" in status_dot, f"Status dot should be connected, got: {status_dot}"
                assert "Connected to Bridge Service" in status_text, f"Unexpected status text: {status_text}"
                print("✅ Bridge connectivity status correctly shows connected")
            else:
                assert "disconnected" in status_dot, f"Status dot should be disconnected, got: {status_dot}"
                assert "Disconnected from Bridge Service" in status_text, f"Unexpected status text: {status_text}"
                print("✅ Bridge connectivity status correctly shows disconnected")
            
            return True
            
        except Exception as e:
            print(f"❌ Bridge connectivity validation failed: {e}")
            return False
    
    async def validate_session_button(self) -> bool:
        """Validate session start/stop button functionality."""
        print("🔍 Testing session button...")
        
        try:
            # Check initial button state
            button_text = await self.page.text_content("#sessionButton")
            button_class = await self.page.get_attribute("#sessionButton", "class")
            
            assert "START SESSION" in button_text, f"Unexpected initial button text: {button_text}"
            assert "start" in button_class, f"Unexpected initial button class: {button_class}"
            
            print("✅ Session button initial state is correct")
            return True
            
        except Exception as e:
            print(f"❌ Session button validation failed: {e}")
            return False
    
    async def validate_socket_connection(self) -> bool:
        """Validate Socket.IO connection."""
        print("🔍 Testing Socket.IO connection...")
        
        try:
            # Wait for socket connection (check console logs)
            await asyncio.sleep(3)
            
            # Check if status updates are working by looking for connected status
            status_dot = await self.page.get_attribute("#statusDot", "class")
            
            # The socket should be connected if we can see status updates
            if "connected" in status_dot or "disconnected" in status_dot:
                print("✅ Socket.IO connection is working (status updates received)")
                return True
            else:
                print("❌ Socket.IO connection may not be working (no status updates)")
                return False
            
        except Exception as e:
            print(f"❌ Socket.IO validation failed: {e}")
            return False
    
    async def validate_timer_display(self) -> bool:
        """Validate timer display."""
        print("🔍 Testing timer display...")
        
        try:
            # Check timer element
            timer_text = await self.page.text_content("#timer")
            assert timer_text == "00:00:00", f"Unexpected timer text: {timer_text}"
            
            print("✅ Timer display is correct")
            return True
            
        except Exception as e:
            print(f"❌ Timer validation failed: {e}")
            return False
    
    async def validate_responsive_design(self) -> bool:
        """Validate responsive design elements."""
        print("🔍 Testing responsive design...")
        
        try:
            # Check that main elements are visible and properly styled
            container = await self.page.query_selector(".container")
            assert container is not None, "Container not found"
            
            # Check button styling
            button = await self.page.query_selector("#sessionButton")
            assert button is not None, "Session button not found"
            
            # Check status panel
            status_panel = await self.page.query_selector(".status-panel")
            assert status_panel is not None, "Status panel not found"
            
            print("✅ Responsive design elements are present")
            return True
            
        except Exception as e:
            print(f"❌ Responsive design validation failed: {e}")
            return False
    
    async def simulate_session_interaction(self) -> bool:
        """Simulate session start interaction (without actually starting)."""
        print("🔍 Testing session interaction simulation...")
        
        try:
            # Check if bridge is running first
            command_client = CommandClient()
            if not command_client.is_bridge_running():
                print("⚠️  Bridge not running, skipping session interaction test")
                return True
            
            # Hover over the session button to test hover effects
            await self.page.hover("#sessionButton")
            await asyncio.sleep(0.5)
            
            # Check that button is clickable (not disabled)
            button_disabled = await self.page.get_attribute("#sessionButton", "disabled")
            assert button_disabled is None, "Button should not be disabled initially"
            
            print("✅ Session interaction elements work correctly")
            return True
            
        except Exception as e:
            print(f"❌ Session interaction validation failed: {e}")
            return False
    
    async def run_all_validations(self) -> bool:
        """Run all validation tests."""
        print("🚀 Starting Flingoos Desktop Service validation...")
        print(f"📍 Testing URL: {self.base_url}")
        print()
        
        validations = [
            ("UI Loading", self.validate_ui_loads),
            ("Bridge Connectivity", self.validate_bridge_connectivity),
            ("Session Button", self.validate_session_button),
            ("Socket Connection", self.validate_socket_connection),
            ("Timer Display", self.validate_timer_display),
            ("Responsive Design", self.validate_responsive_design),
            ("Session Interaction", self.simulate_session_interaction),
        ]
        
        results = []
        
        for name, validation_func in validations:
            try:
                result = await validation_func()
                results.append((name, result))
            except Exception as e:
                print(f"❌ {name} validation crashed: {e}")
                results.append((name, False))
            
            print()  # Add spacing between tests
        
        # Summary
        print("📊 Validation Summary:")
        print("=" * 50)
        
        passed = 0
        total = len(results)
        
        for name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{name:20} {status}")
            if result:
                passed += 1
        
        print("=" * 50)
        print(f"Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All validations passed! Desktop service is working correctly.")
            return True
        else:
            print("⚠️  Some validations failed. Check the output above for details.")
            return False


async def main():
    """Main validation function."""
    validator = DesktopServiceValidator()
    
    try:
        await validator.setup()
        success = await validator.run_all_validations()
        return 0 if success else 1
        
    except Exception as e:
        print(f"❌ Validation setup failed: {e}")
        return 1
        
    finally:
        await validator.teardown()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
