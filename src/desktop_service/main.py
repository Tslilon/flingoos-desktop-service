"""
Main entry point for the Flingoos Desktop Service.

This module provides the main application logic for running the desktop service
independently from the bridge, with local run mechanisms and management commands.
"""

import argparse
import logging
import sys
import time
import signal
from pathlib import Path
from typing import Optional

from .ui.web_server import D4WebServer
from .bridge_client.command_client import CommandClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('desktop_service.log')
    ]
)
logger = logging.getLogger(__name__)


class DesktopService:
    """Main desktop service application."""
    
    def __init__(self, port: int = 8844):
        self.port = port
        self.web_server = None
        self.running = False
        
    def start(self):
        """Start the desktop service."""
        if self.running:
            logger.warning("Desktop service is already running")
            return
            
        logger.info(f"Starting Flingoos Desktop Service on port {self.port}")
        
        # Check if bridge is running
        command_client = CommandClient()
        if not command_client.is_bridge_running():
            logger.warning("Bridge service is not running. Some features may not work.")
            logger.info("To start bridge: python3 -m bridge.main run")
        else:
            logger.info("Bridge service detected and responsive")
        
        # Start web server
        try:
            self.web_server = D4WebServer(port=self.port)
            self.web_server.run()
            self.running = True
            
            logger.info(f"✅ Desktop Service started successfully!")
            logger.info(f"🌐 Web UI available at: http://127.0.0.1:{self.port}")
            logger.info("🛑 Press Ctrl+C to stop")
            
        except Exception as e:
            logger.error(f"Failed to start desktop service: {e}")
            raise
    
    def stop(self):
        """Stop the desktop service."""
        if not self.running:
            return
            
        logger.info("Stopping desktop service...")
        
        if self.web_server:
            self.web_server.stop()
            
        self.running = False
        logger.info("Desktop service stopped")
    
    def is_running(self) -> bool:
        """Check if the service is running."""
        return self.running and self.web_server and self.web_server.is_running()


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Flingoos Desktop Service - Session Management UI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m desktop_service start              # Start on default port 8844
  python -m desktop_service start --port 9000  # Start on custom port
  python -m desktop_service status             # Check if running
  python -m desktop_service stop               # Stop the service
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Start command
    start_parser = subparsers.add_parser('start', help='Start the desktop service')
    start_parser.add_argument(
        '--port',
        type=int,
        default=8844,
        help='Port to run the web server on (default: 8844)'
    )
    start_parser.add_argument(
        '--no-browser',
        action='store_true',
        help='Do not automatically open browser'
    )
    
    # Status command
    subparsers.add_parser('status', help='Check service status')
    
    # Stop command
    subparsers.add_parser('stop', help='Stop the service')
    
    return parser


def check_bridge_status():
    """Check and report bridge service status."""
    command_client = CommandClient()
    
    try:
        if command_client.is_bridge_running():
            response = command_client.get_status()
            print("✅ Bridge service is running and responsive")
            print(f"   Status: {response}")
            return True
        else:
            print("❌ Bridge service is not running")
            print("   Start it with: python3 -m bridge.main run")
            return False
    except Exception as e:
        print(f"❌ Error checking bridge status: {e}")
        return False


def get_pid_file() -> Path:
    """Get the path to the PID file."""
    return Path.cwd() / "desktop_service.pid"


def save_pid():
    """Save current process PID to file."""
    import os
    pid_file = get_pid_file()
    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))


def is_service_running() -> tuple[bool, Optional[int]]:
    """Check if service is already running."""
    pid_file = get_pid_file()
    if not pid_file.exists():
        return False, None
    
    try:
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        
        # Check if process is still running
        try:
            import os
            os.kill(pid, 0)  # This doesn't kill, just checks if process exists
            return True, pid
        except OSError:
            # Process doesn't exist, remove stale PID file
            pid_file.unlink()
            return False, None
            
    except (ValueError, FileNotFoundError):
        return False, None


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == 'status':
        running, pid = is_service_running()
        if running:
            print(f"✅ Desktop Service is running (PID: {pid})")
            print(f"   Web UI: http://127.0.0.1:8844")
        else:
            print("❌ Desktop Service is not running")
        
        # Also check bridge status
        print("\nBridge Status:")
        check_bridge_status()
        return 0
    
    elif args.command == 'stop':
        running, pid = is_service_running()
        if not running:
            print("Desktop Service is not running")
            return 0
        
        try:
            import os
            os.kill(pid, signal.SIGTERM)
            
            # Wait for process to stop
            for _ in range(10):  # Wait up to 10 seconds
                time.sleep(1)
                try:
                    os.kill(pid, 0)
                except OSError:
                    break
            else:
                # Force kill if it didn't stop gracefully
                print("Force stopping service...")
                os.kill(pid, signal.SIGKILL)
            
            # Remove PID file
            pid_file = get_pid_file()
            if pid_file.exists():
                pid_file.unlink()
                
            print("✅ Desktop Service stopped successfully")
            return 0
            
        except OSError as e:
            print(f"❌ Error stopping service: {e}")
            return 1
    
    elif args.command == 'start':
        # Check if already running
        running, pid = is_service_running()
        if running:
            print(f"Desktop Service is already running (PID: {pid})")
            print(f"Access it at: http://127.0.0.1:{args.port}")
            return 0
        
        # Start the service
        service = DesktopService(port=args.port)
        
        # Set up signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info("Received shutdown signal")
            service.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Save PID
            import os
            save_pid()
            
            # Start service
            service.start()
            
            # Keep running until interrupted
            while service.is_running():
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        except Exception as e:
            logger.error(f"Service error: {e}")
            return 1
        finally:
            service.stop()
            # Clean up PID file
            pid_file = get_pid_file()
            if pid_file.exists():
                pid_file.unlink()
        
        return 0
    
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
