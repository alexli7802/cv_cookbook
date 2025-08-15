"""Custom exceptions for the pose detection application."""


class PoseDetectionError(Exception):
    """Base exception for pose detection application."""

    pass


class VideoProcessingError(PoseDetectionError):
    """Raised when video processing fails."""

    pass


class InvalidVideoFormatError(VideoProcessingError):
    """Raised when video format is not supported."""

    pass


class VideoTooLargeError(VideoProcessingError):
    """Raised when video exceeds size or duration limits."""

    pass


class FrameProcessingError(VideoProcessingError):
    """Raised when individual frame processing fails."""

    pass


class FileUploadError(PoseDetectionError):
    """Raised when file upload fails."""

    pass


class SecurityError(PoseDetectionError):
    """Raised when security validation fails."""

    pass
