#!/usr/bin/env python3
"""
GUI Import Test - SAVE POINT #153
Verify AI modules can be imported in GUI context
"""

import sys
from pathlib import Path

# CRITICAL: Point to project root (parent directory)
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from AI.match_analyzer import analyze_match
    from AI.tailor_engine import tailor_resume, generate_cover_letter
    from config.settings import MIN_MATCH_THRESHOLD
    print("SUCCESS: All imports working")
    print(f"MIN_MATCH_THRESHOLD: {MIN_MATCH_THRESHOLD}")
except Exception as e:
    print(f"IMPORT ERROR: {e}")
    sys.exit(1)
