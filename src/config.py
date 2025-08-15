"""Configuration management for the pose detection application."""

import os
from pathlib import Path


class Config:
    """Application configuration with environment-based settings."""

    # Base paths
    BASE_DIR = Path(__file__).parent.parent
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    TEMPLATE_FOLDER = BASE_DIR / "templates"
    STATIC_FOLDER = BASE_DIR / "static"

    # File upload settings
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB
    ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"}
    MAX_FILENAME_LENGTH = 255

    # MediaPipe settings
    POSE_MODEL_COMPLEXITY = 1
    POSE_MIN_DETECTION_CONFIDENCE = 0.5
    POSE_MIN_TRACKING_CONFIDENCE = 0.5

    # Video processing settings
    MAX_VIDEO_DURATION_SECONDS = 300  # 5 minutes
    MAX_VIDEO_RESOLUTION = (1920, 1080)
    SUPPORTED_CODECS = ["mp4v", "XVID", "MJPG"]

    # Performance settings
    FRAME_CACHE_SIZE = 100
    VIDEO_CACHE_TTL_SECONDS = 3600  # 1 hour

    # Security settings
    SECURE_FILENAME_CHARS = set(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    )

    # Flask settings
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-in-production")
    DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    HOST = os.environ.get("FLASK_HOST", "127.0.0.1")
    PORT = int(os.environ.get("FLASK_PORT", 8080))

    @classmethod
    def init_directories(cls):
        """Create necessary directories if they don't exist."""
        cls.UPLOAD_FOLDER.mkdir(exist_ok=True)
        cls.STATIC_FOLDER.mkdir(exist_ok=True)

    @classmethod
    def is_allowed_video_file(cls, filename: str) -> bool:
        """Check if the file has an allowed video extension."""
        return Path(filename).suffix.lower() in cls.ALLOWED_VIDEO_EXTENSIONS

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitize filename to prevent path traversal and other issues."""
        # Remove path components
        filename = Path(filename).name

        # Limit length
        if len(filename) > cls.MAX_FILENAME_LENGTH:
            name, ext = os.path.splitext(filename)
            max_name_length = cls.MAX_FILENAME_LENGTH - len(ext)
            filename = name[:max_name_length] + ext

        # Keep only safe characters
        safe_chars = "".join(
            c if c in cls.SECURE_FILENAME_CHARS else "_" for c in filename
        )

        # Ensure we have a valid filename
        if not safe_chars or safe_chars.startswith("."):
            safe_chars = f"video_{safe_chars}"

        return safe_chars
