# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a computer vision cookbook for sports applications, featuring practical implementations of pose detection and motion analysis using MediaPipe. The repository contains examples and reference materials for building sports CV applications.

## Key Dependencies

The main Python script requires:
- OpenCV (`cv2`) - Video processing and computer vision operations
- MediaPipe (`mediapipe`) - Google's pose detection framework  
- NumPy (`numpy`) - Numerical computations for pose analysis
- OS module - File system operations

Install dependencies with:
```bash
pip install opencv-python mediapipe numpy
```

## Repository Structure

- `src/mediapipe_demo.py` - Main demonstration script for video pose detection
- `data/` - Contains sample video files (LJ.mov, TJ.MOV, run.MOV) for testing
- `SPECS.md` - Comprehensive documentation of computer vision models for sports applications

## Running the Demo

To run pose detection on a video:

```bash
python src/mediapipe_demo.py
```

Note: Update the `input_video` path in the main section to point to your video file. The script provides two analysis modes:
1. Video processing with pose overlay output
2. Pose data analysis with angle calculations

## Core Functionality

The main script (`src/mediapipe_demo.py`) provides:

### Video Processing (`process_video`)
- Processes video files for real-time pose detection
- Outputs annotated video with pose landmarks
- Configurable confidence thresholds and model complexity
- Progress tracking and frame-by-frame analysis

### Pose Analysis (`analyze_pose_data`) 
- Extracts quantitative metrics from pose data
- Calculates joint angles (e.g., arm angles for sports analysis)
- Provides statistical summaries of movement patterns

## Development Notes

- The script uses MediaPipe's Pose solution with 33 keypoints
- Video output uses mp4v codec for compatibility
- RGB/BGR conversion required for MediaPipe processing
- Default model complexity is set to 1 (balanced speed/accuracy)
- Frame display can be disabled for faster batch processing

## Sports CV Reference

`SPECS.md` contains comprehensive information about:
- Image and video processing models for sports
- Performance benchmarks and hardware requirements  
- Implementation frameworks and deployment strategies
- Real-world accuracy metrics and cost-effectiveness analysis