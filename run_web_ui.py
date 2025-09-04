#!/usr/bin/env python3
"""
Run script for the Flingoos Web UI (Desktop Service)
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from web_ui.web_server import WebUIServer

def main():
    """Run the Web UI server"""
    print("🚀 Starting Flingoos Web UI...")
    
    try:
        server = WebUIServer(port=8844)
        server.run()
    except KeyboardInterrupt:
        print("\n🛑 Web UI stopped by user")
    except Exception as e:
        print(f"❌ Error starting Web UI: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()