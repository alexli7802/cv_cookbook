"""Simple Flask web application for pose detection demo.

This is a simplified version of the main web application,
suitable for demonstrations and testing.
"""

from flask import Flask, render_template, request, jsonify
import cv2
import mediapipe as mp
import os
import base64
from werkzeug.utils import secure_filename

app = Flask(__name__, template_folder="../templates")
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500MB max

# Create uploads directory
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# MediaPipe setup
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

# Global variables
current_video = None
video_properties = {}


@app.route("/")
def index():
    return render_template("simple.html")


@app.route("/upload", methods=["POST"])
def upload_video():
    global current_video, video_properties

    if "video" not in request.files:
        return jsonify({"error": "No video file"}), 400

    file = request.files["video"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    # Get video properties
    cap = cv2.VideoCapture(filepath)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = frame_count / fps if fps > 0 else 0
    cap.release()

    current_video = filepath
    video_properties = {
        "fps": fps,
        "frames": frame_count,
        "width": width,
        "height": height,
        "duration": duration,
        "filename": filename,
    }

    return jsonify({"success": True, "properties": video_properties})


@app.route("/process_frame/<int:frame_num>")
def process_frame(frame_num):
    global current_video

    if not current_video or not os.path.exists(current_video):
        return jsonify({"error": "No video loaded"}), 400

    cap = cv2.VideoCapture(current_video)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)

    ret, frame = cap.read()
    if not ret:
        cap.release()
        return jsonify({"error": "Could not read frame"}), 400

    # Create a fresh pose detector for each frame to avoid timestamp issues
    with mp_pose.Pose(
        model_complexity=1, min_detection_confidence=0.5, min_tracking_confidence=0.5
    ) as pose_detector:
        # Process with MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose_detector.process(rgb_frame)

        # Draw pose landmarks
        if results.pose_landmarks:
            mp_drawing.draw_landmarks(
                frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS
            )

    # Convert to base64 for web display
    _, buffer = cv2.imencode(".jpg", frame)
    frame_base64 = base64.b64encode(buffer).decode("utf-8")

    cap.release()

    return jsonify(
        {
            "frame": f"data:image/jpeg;base64,{frame_base64}",
            "has_pose": results.pose_landmarks is not None,
        }
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
