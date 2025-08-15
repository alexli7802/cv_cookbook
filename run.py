#!/usr/bin/env python3
"""
Production entry point for the Pose Detection Application.

This script provides a production-ready way to run the application
with proper configuration and error handling.
"""

import sys
import os
import logging
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

try:
    from src.web_app import create_app
    from src.config import Config
except ImportError as e:
    print(f"Failed to import application modules: {e}")
    print("Make sure you're running from the project root directory")
    sys.exit(1)


def setup_logging():
    """Configure logging for production."""
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('pose_detection.log', mode='a')
        ]
    )


def main():
    """Main entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Create application
        app = create_app()
        
        # Run application
        logger.info(f"Starting Pose Detection Application on {Config.HOST}:{Config.PORT}")
        logger.info(f"Debug mode: {Config.DEBUG}")
        
        app.run(
            host=Config.HOST,
            port=Config.PORT,
            debug=Config.DEBUG,
            threaded=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()