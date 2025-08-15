"""Video file management and session handling."""

import time
from pathlib import Path
from typing import Dict, Optional
from threading import Lock
import logging
from dataclasses import dataclass

from config import Config
from exceptions import FileUploadError, SecurityError
from pose_detector import VideoMetadata


logger = logging.getLogger(__name__)


@dataclass
class VideoSession:
    """Represents an active video session."""

    file_path: Path
    metadata: VideoMetadata
    upload_time: float
    last_accessed: float


class VideoManager:
    """Manages video file uploads and sessions."""

    def __init__(self):
        """Initialize the video manager."""
        self._sessions: Dict[str, VideoSession] = {}
        self._lock = Lock()
        Config.init_directories()

    def save_uploaded_file(self, file, session_id: str) -> Path:
        """
        Save uploaded file with security validations.

        Args:
            file: Uploaded file object
            session_id: Unique session identifier

        Returns:
            Path to the saved file

        Raises:
            FileUploadError: If file upload fails
            SecurityError: If security validation fails
        """
        if not file or not file.filename:
            raise FileUploadError("No file provided")

        # Security validations
        original_filename = file.filename
        if not Config.is_allowed_video_file(original_filename):
            allowed_exts = ", ".join(Config.ALLOWED_VIDEO_EXTENSIONS)
            raise SecurityError(f"File type not allowed. Allowed types: {allowed_exts}")

        # Sanitize filename
        safe_filename = Config.sanitize_filename(original_filename)
        if not safe_filename:
            raise SecurityError("Invalid filename")

        # Create unique filename to prevent conflicts
        timestamp = int(time.time())
        unique_filename = f"{session_id}_{timestamp}_{safe_filename}"
        file_path = Config.UPLOAD_FOLDER / unique_filename

        try:
            # Save file
            file.save(str(file_path))

            # Verify file was saved and is readable
            if not file_path.exists():
                raise FileUploadError("File was not saved successfully")

            file_size = file_path.stat().st_size
            if file_size == 0:
                file_path.unlink(missing_ok=True)
                raise FileUploadError("Uploaded file is empty")

            if file_size > Config.MAX_CONTENT_LENGTH:
                file_path.unlink(missing_ok=True)
                raise FileUploadError(
                    f"File too large. Maximum size: "
                    f"{Config.MAX_CONTENT_LENGTH // (1024*1024)}MB"
                )

            logger.info(
                f"Successfully saved uploaded file: {file_path} ({file_size} bytes)"
            )
            return file_path

        except OSError as e:
            logger.error(f"Failed to save uploaded file: {e}")
            # Clean up partial file if it exists
            if file_path.exists():
                file_path.unlink(missing_ok=True)
            raise FileUploadError(f"Failed to save file: {e}")

    def create_session(
        self, session_id: str, file_path: Path, metadata: VideoMetadata
    ) -> VideoSession:
        """Create a new video session."""
        current_time = time.time()
        session = VideoSession(
            file_path=file_path,
            metadata=metadata,
            upload_time=current_time,
            last_accessed=current_time,
        )

        with self._lock:
            # Clean up old session if it exists
            self._cleanup_session(session_id)
            self._sessions[session_id] = session

        logger.info(f"Created video session: {session_id}")
        return session

    def get_session(self, session_id: str) -> Optional[VideoSession]:
        """Get an active video session."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.last_accessed = time.time()
                # Verify file still exists
                if not session.file_path.exists():
                    logger.warning(
                        f"Video file missing for session {session_id}, "
                        f"cleaning up session"
                    )
                    del self._sessions[session_id]
                    return None
            return session

    def remove_session(self, session_id: str) -> bool:
        """Remove a video session and clean up associated files."""
        with self._lock:
            return self._cleanup_session(session_id)

    def _cleanup_session(self, session_id: str) -> bool:
        """Internal method to clean up a session."""
        session = self._sessions.get(session_id)
        if session:
            # Remove file if it exists
            try:
                if session.file_path.exists():
                    session.file_path.unlink()
                    logger.info(f"Cleaned up file: {session.file_path}")
            except OSError as e:
                logger.error(f"Failed to delete file {session.file_path}: {e}")

            # Remove session
            del self._sessions[session_id]
            return True
        return False

    def cleanup_expired_sessions(self):
        """Clean up sessions that have exceeded TTL."""
        current_time = time.time()
        expired_sessions = []

        with self._lock:
            for session_id, session in self._sessions.items():
                if (
                    current_time - session.last_accessed
                    > Config.VIDEO_CACHE_TTL_SECONDS
                ):
                    expired_sessions.append(session_id)

        for session_id in expired_sessions:
            self.remove_session(session_id)
            logger.info(f"Cleaned up expired session: {session_id}")

    def get_session_count(self) -> int:
        """Get the number of active sessions."""
        with self._lock:
            return len(self._sessions)

    def get_total_storage_used(self) -> int:
        """Get total storage used by all uploaded files."""
        total_size = 0
        with self._lock:
            for session in self._sessions.values():
                try:
                    if session.file_path.exists():
                        total_size += session.file_path.stat().st_size
                except OSError:
                    pass  # File might have been deleted
        return total_size
