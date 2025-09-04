#!/usr/bin/env python3
"""
Flingoos Desktop Service Runner

Simple script to run the desktop service with proper Python path setup.
"""

import sys
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from desktop_service.main import main

if __name__ == "__main__":
    sys.exit(main())
