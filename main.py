# main.py
"""
MediFlow — Stage 4 Entry Point.

Usage:
    python main.py --demo                    # Quick test with sample data
    python main.py --text "..." --patient X  # Text input mode
    python main.py --audio file.wav --patient X  # Audio mode
"""
from clinical_workflow.runner import main

if __name__ == "__main__":
    main()
