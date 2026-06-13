"""Entry point for plm-tcin-mapper-client Streamlit application.

This module provides the start() function used by the entrypoint.sh script.
The streamlit_app.py is the actual Streamlit application definition.
"""

import os
import subprocess
import sys


def start() -> None:
    """Start the Streamlit application.

    This is called by entrypoint.sh. The environment variable API_BASE_URL
    should be set to point to the plm-tcin-mapper-api service.
    """
    app_port = os.environ.get("APP_PORT", "8080")
    streamlit_script = os.path.join(os.path.dirname(__file__), "streamlit_app.py")

    # Run Streamlit with configuration for production deployment
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            streamlit_script,
            f"--server.port={app_port}",
            "--server.address=0.0.0.0",
            "--server.headless=true",
            "--logger.level=info",
        ],
        check=True,
    )
