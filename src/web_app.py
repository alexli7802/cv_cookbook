"""Refactored Flask web application for pose detection.

This module provides a web interface for uploading videos and detecting poses
using MediaPipe. The application follows industry best practices for security,
error handling, and code organization.
"""

import logging
import uuid
from flask import Flask, render_template, request, jsonify, session
from werkzeug.exceptions import RequestEntityTooLarge

from config import Config
from exceptions import (
    VideoProcessingError,
    FileUploadError,
    SecurityError,
    FrameProcessingError,
)
from pose_detector import PoseDetectionService
from video_manager import VideoManager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize Flask application
app = Flask(
    __name__,
    template_folder=str(Config.TEMPLATE_FOLDER),
    static_folder=str(Config.STATIC_FOLDER),
    static_url_path="/static",
)
app.config.update(
    SECRET_KEY=Config.SECRET_KEY,
    MAX_CONTENT_LENGTH=Config.MAX_CONTENT_LENGTH,
    UPLOAD_FOLDER=str(Config.UPLOAD_FOLDER),
)

# Initialize services
pose_service = PoseDetectionService()
video_manager = VideoManager()


@app.route("/")
def index():
    """Render the main application page."""
    # Generate session ID if not exists
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())

    return render_template("simple.html")


@app.route("/upload", methods=["POST"])
def upload_video():
    """Handle video file upload with comprehensive validation and error handling."""
    try:
        # Validate request
        if "video" not in request.files:
            return jsonify({"error": "No video file provided"}), 400

        file = request.files["video"]
        if not file or file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        # Get or create session ID
        session_id = session.get("session_id")
        if not session_id:
            session_id = str(uuid.uuid4())
            session["session_id"] = session_id

        # Save uploaded file
        file_path = video_manager.save_uploaded_file(file, session_id)

        # Extract video metadata
        metadata = pose_service.get_video_metadata(str(file_path))

        # Create session
        video_manager.create_session(session_id, file_path, metadata)

        logger.info(
            f"Successfully uploaded video for session {session_id}: {metadata.filename}"
        )

        return jsonify(
            {
                "success": True,
                "properties": {
                    "fps": metadata.fps,
                    "frames": metadata.frame_count,
                    "width": metadata.width,
                    "height": metadata.height,
                    "duration": metadata.duration,
                    "filename": metadata.filename,
                    "codec": metadata.codec,
                },
            }
        )

    except SecurityError as e:
        logger.warning(f"Security error during upload: {e}")
        return jsonify({"error": str(e)}), 400

    except FileUploadError as e:
        logger.error(f"File upload error: {e}")
        return jsonify({"error": str(e)}), 400

    except VideoProcessingError as e:
        logger.error(f"Video processing error: {e}")
        return jsonify({"error": f"Video processing failed: {e}"}), 400

    except Exception as e:
        logger.error(f"Unexpected error during upload: {e}")
        return jsonify({"error": "Upload failed due to unexpected error"}), 500


@app.route("/process_frame/<int:frame_num>")
def process_frame(frame_num):
    """Process a specific frame and return pose detection results."""
    try:
        # Get session
        session_id = session.get("session_id")
        if not session_id:
            return jsonify({"error": "No active session"}), 400

        video_session = video_manager.get_session(session_id)
        if not video_session:
            return jsonify({"error": "No video loaded for this session"}), 400

        # Validate frame number
        if frame_num < 0:
            return jsonify({"error": "Frame number must be non-negative"}), 400

        if frame_num >= video_session.metadata.frame_count:
            return (
                jsonify(
                    {
                        "error": f"Frame {frame_num} out of range "
                        f"(0-{video_session.metadata.frame_count-1})"
                    }
                ),
                400,
            )

        # Process frame
        result = pose_service.process_frame(str(video_session.file_path), frame_num)

        response_data = {"frame": result.frame_base64, "has_pose": result.has_pose}

        # Include confidence if available
        if result.confidence is not None:
            response_data["confidence"] = round(result.confidence, 3)

        return jsonify(response_data)

    except FrameProcessingError as e:
        logger.error(f"Frame processing error for frame {frame_num}: {e}")
        return jsonify({"error": f"Frame processing failed: {e}"}), 400

    except Exception as e:
        logger.error(f"Unexpected error processing frame {frame_num}: {e}")
        return (
            jsonify({"error": "Frame processing failed due to unexpected error"}),
            500,
        )


@app.route("/session_info")
def session_info():
    """Get information about the current session."""
    session_id = session.get("session_id")
    if not session_id:
        return jsonify({"error": "No active session"}), 400

    video_session = video_manager.get_session(session_id)
    if not video_session:
        return jsonify({"session_active": False})

    return jsonify(
        {
            "session_active": True,
            "upload_time": video_session.upload_time,
            "last_accessed": video_session.last_accessed,
            "file_size": video_session.file_path.stat().st_size
            if video_session.file_path.exists()
            else 0,
        }
    )


@app.route("/cleanup_session", methods=["POST"])
def cleanup_session():
    """Clean up the current session and associated files."""
    session_id = session.get("session_id")
    if session_id:
        success = video_manager.remove_session(session_id)
        session.pop("session_id", None)
        return jsonify({"success": success})

    return jsonify({"success": False, "error": "No active session"})


@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    """Handle file size exceeded error."""
    max_size_mb = Config.MAX_CONTENT_LENGTH // (1024 * 1024)
    return (
        jsonify({"error": f"File too large. Maximum size allowed: {max_size_mb}MB"}),
        413,
    )


@app.errorhandler(500)
def handle_internal_error(e):
    """Handle internal server errors."""
    logger.error(f"Internal server error: {e}")
    return jsonify({"error": "Internal server error"}), 500


def create_app():
    """Application factory function."""
    # Clean up expired sessions on startup
    video_manager.cleanup_expired_sessions()
    return app


if __name__ == "__main__":
    # Configure logging for development
    logging.basicConfig(level=logging.DEBUG)

    # Create application
    application = create_app()

    # Run development server
    logger.info(f"Starting development server on {Config.HOST}:{Config.PORT}")
    application.run(debug=Config.DEBUG, host=Config.HOST, port=Config.PORT)
