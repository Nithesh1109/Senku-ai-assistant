"""
Senku 3.0 — Root Entry Point
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from senku.main import main

if __name__ == "__main__":
    main()
