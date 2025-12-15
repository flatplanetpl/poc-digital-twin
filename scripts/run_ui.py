#!/usr/bin/env python3
"""Script to run the Streamlit UI."""

import subprocess
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings


def main():
    """Run the Streamlit application."""
    app_path = Path(__file__).parent.parent / "src" / "ui" / "app.py"

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(settings.streamlit_port),
        "--server.headless",
        "true",
    ]

    print(f"Starting Digital Twin UI on http://localhost:{settings.streamlit_port}")
    subprocess.run(cmd)


if __name__ == "__main__":
    main()
