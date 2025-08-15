"""MediaPipe-based pose detection service."""

import cv2
import mediapipe as mp
import numpy as np
import base64
from typing import Optional, Any
from dataclasses import dataclass
from contextlib import contextmanager
import logging

from config import Config
from exceptions import FrameProcessingError, VideoProcessingError


logger = logging.getLogger(__name__)


@dataclass
class PoseResult:
    """Result of pose detection on a frame."""

    frame_base64: str
    has_pose: bool
    landmarks: Optional[Any] = None
    confidence: Optional[float] = None


@dataclass
class VideoMetadata:
    """Metadata for a video file."""

    fps: int
    frame_count: int
    width: int
    height: int
    duration: float
    filename: str
    codec: str


class PoseDetectionService:
    """Service for detecting poses in video frames using MediaPipe."""

    def __init__(self):
        """Initialize the pose detection service."""
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.pose = self.mp_pose.Pose(
            model_complexity=Config.POSE_MODEL_COMPLEXITY,
            min_detection_confidence=Config.POSE_MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=Config.POSE_MIN_TRACKING_CONFIDENCE,
        )

    @contextmanager
    def video_capture(self, video_path: str):
        """Context manager for video capture with proper resource cleanup."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise VideoProcessingError(f"Cannot open video file: {video_path}")

        try:
            yield cap
        finally:
            cap.release()

    def get_video_metadata(self, video_path: str) -> VideoMetadata:
        """Extract metadata from video file."""
        try:
            with self.video_capture(video_path) as cap:
                fps = int(cap.get(cv2.CAP_PROP_FPS))
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))

                # Convert fourcc to string
                codec = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])

                duration = frame_count / fps if fps > 0 else 0

                # Validate video constraints
                if duration > Config.MAX_VIDEO_DURATION_SECONDS:
                    raise VideoProcessingError(
                        f"Video duration ({duration:.1f}s) exceeds maximum allowed "
                        f"({Config.MAX_VIDEO_DURATION_SECONDS}s)"
                    )

                if (
                    width > Config.MAX_VIDEO_RESOLUTION[0]
                    or height > Config.MAX_VIDEO_RESOLUTION[1]
                ):
                    raise VideoProcessingError(
                        f"Video resolution ({width}x{height}) exceeds maximum allowed "
                        f"({Config.MAX_VIDEO_RESOLUTION[0]}x"
                        f"{Config.MAX_VIDEO_RESOLUTION[1]})"
                    )

                return VideoMetadata(
                    fps=fps,
                    frame_count=frame_count,
                    width=width,
                    height=height,
                    duration=duration,
                    filename=video_path.split("/")[-1],
                    codec=codec,
                )

        except cv2.error as e:
            logger.error(f"OpenCV error while reading video metadata: {e}")
            raise VideoProcessingError(f"Failed to read video metadata: {e}")
        except Exception as e:
            logger.error(f"Unexpected error while reading video metadata: {e}")
            raise VideoProcessingError(f"Unexpected error: {e}")

    def process_frame(self, video_path: str, frame_number: int) -> PoseResult:
        """Process a specific frame and return pose detection results."""
        try:
            with self.video_capture(video_path) as cap:
                # Validate frame number
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if frame_number < 0 or frame_number >= total_frames:
                    raise FrameProcessingError(
                        f"Frame number {frame_number} is out of range "
                        f"(0-{total_frames-1})"
                    )

                # Seek to the specific frame
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                ret, frame = cap.read()

                if not ret:
                    raise FrameProcessingError(f"Could not read frame {frame_number}")

                return self._process_frame_data(frame)

        except cv2.error as e:
            logger.error(f"OpenCV error while processing frame {frame_number}: {e}")
            raise FrameProcessingError(f"OpenCV error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error while processing frame {frame_number}: {e}")
            raise FrameProcessingError(f"Unexpected error: {e}")

    def _process_frame_data(self, frame: np.ndarray) -> PoseResult:
        """Process frame data and detect poses."""
        # Convert BGR to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Create a fresh pose detector for each frame to avoid timestamp issues
        with self.mp_pose.Pose(
            model_complexity=Config.POSE_MODEL_COMPLEXITY,
            min_detection_confidence=Config.POSE_MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=Config.POSE_MIN_TRACKING_CONFIDENCE,
        ) as pose_detector:
            # Run pose detection
            results = pose_detector.process(rgb_frame)

            # Draw pose landmarks if detected
            has_pose = results.pose_landmarks is not None
            confidence = None

            if has_pose:
                self.mp_drawing.draw_landmarks(
                    frame,
                    results.pose_landmarks,
                    self.mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=self.mp_drawing.DrawingSpec(
                        color=(0, 255, 0), thickness=2, circle_radius=2
                    ),
                    connection_drawing_spec=self.mp_drawing.DrawingSpec(
                        color=(0, 255, 255), thickness=2
                    ),
                )

                # Calculate average confidence if landmarks are available
                if results.pose_landmarks.landmark:
                    confidences = [
                        lm.visibility
                        for lm in results.pose_landmarks.landmark
                        if hasattr(lm, "visibility")
                    ]
                    confidence = np.mean(confidences) if confidences else None

        # Encode frame as JPEG and convert to base64
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 85]
        success, buffer = cv2.imencode(".jpg", frame, encode_params)

        if not success:
            raise FrameProcessingError("Failed to encode frame as JPEG")

        frame_base64 = base64.b64encode(buffer).decode("utf-8")

        return PoseResult(
            frame_base64=f"data:image/jpeg;base64,{frame_base64}",
            has_pose=has_pose,
            landmarks=results.pose_landmarks if has_pose else None,
            confidence=confidence,
        )

    def cleanup(self):
        """Clean up resources."""
        if hasattr(self, "pose") and self.pose:
            self.pose.close()
