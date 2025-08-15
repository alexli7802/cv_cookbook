/**
 * Video Player Module for Pose Detection Application
 * 
 * This module handles video playback, frame processing, and user interface interactions
 * for the pose detection web application. It follows modern JavaScript practices with
 * proper error handling, modular design, and clear separation of concerns.
 */

class VideoPlayer {
    constructor() {
        this.videoProperties = null;
        this.currentFrame = 0;
        this.isPlaying = false;
        this.playInterval = null;
        this.frameRequestController = new AbortController();
        
        this.initializeElements();
        this.attachEventListeners();
        this.initializeUI();
    }
    
    /**
     * Initialize DOM element references
     */
    initializeElements() {
        this.elements = {
            videoInput: document.getElementById('videoInput'),
            selectBtn: document.getElementById('selectBtn'),
            playBtn: document.getElementById('playBtn'),
            stopBtn: document.getElementById('stopBtn'),
            properties: document.getElementById('properties'),
            videoFrame: document.getElementById('videoFrame'),
            videoPlaceholder: document.getElementById('videoPlaceholder'),
            frameControls: document.getElementById('frameControls'),
            frameSlider: document.getElementById('frameSlider'),
            progressBar: document.getElementById('progressBar'),
            currentFrameSpan: document.getElementById('currentFrame'),
            totalFramesSpan: document.getElementById('totalFrames'),
            loadingIndicator: document.getElementById('loadingIndicator'),
            errorMessage: document.getElementById('errorMessage')
        };
    }
    
    /**
     * Attach event listeners to UI elements
     */
    attachEventListeners() {
        this.elements.selectBtn.addEventListener('click', () => this.elements.videoInput.click());
        
        this.elements.videoInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) this.handleVideoUpload(file);
        });
        
        this.elements.playBtn.addEventListener('click', () => {
            this.isPlaying ? this.pauseVideo() : this.playVideo();
        });
        
        this.elements.stopBtn.addEventListener('click', () => this.stopVideo());
        
        this.elements.frameSlider.addEventListener('input', (e) => {
            if (this.videoProperties) {
                this.seekToFrame(parseInt(e.target.value));
            }
        });
        
        // Handle page unload to clean up resources
        window.addEventListener('beforeunload', () => this.cleanup());
        
        // Handle keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));
    }
    
    /**
     * Initialize UI state
     */
    initializeUI() {
        this.setLoadingState(false);
        this.showError(null);
        this.updateUIState();
    }
    
    /**
     * Handle keyboard shortcuts
     */
    handleKeyboardShortcuts(event) {
        if (!this.videoProperties) return;
        
        switch (event.code) {
            case 'Space':
                event.preventDefault();
                this.isPlaying ? this.pauseVideo() : this.playVideo();
                break;
            case 'ArrowLeft':
                event.preventDefault();
                this.seekToFrame(Math.max(0, this.currentFrame - 1));
                break;
            case 'ArrowRight':
                event.preventDefault();
                this.seekToFrame(Math.min(this.videoProperties.frames - 1, this.currentFrame + 1));
                break;
            case 'Home':
                event.preventDefault();
                this.seekToFrame(0);
                break;
            case 'End':
                event.preventDefault();
                this.seekToFrame(this.videoProperties.frames - 1);
                break;
        }
    }
    
    /**
     * Handle video file upload
     */
    async handleVideoUpload(file) {
        try {
            this.setLoadingState(true, 'Uploading video...');
            this.showError(null);
            
            // Validate file before upload
            this.validateVideoFile(file);
            
            const response = await this.uploadVideo(file);
            
            if (response.success) {
                this.videoProperties = response.properties;
                this.updateVideoProperties();
                this.setupFrameControls();
                this.updateUIState();
                this.currentFrame = 0;
                await this.displayFrame(0);
                this.showSuccess('Video uploaded successfully!');
            } else {
                throw new Error(response.error || 'Upload failed');
            }
        } catch (error) {
            this.showError(`Upload failed: ${error.message}`);
            console.error('Upload error:', error);
        } finally {
            this.setLoadingState(false);
        }
    }
    
    /**
     * Validate video file before upload
     */
    validateVideoFile(file) {
        const maxSize = 500 * 1024 * 1024; // 500MB
        const allowedTypes = [
            'video/mp4', 'video/avi', 'video/quicktime', 'video/x-msvideo',
            'video/webm', 'video/x-matroska'
        ];
        
        if (file.size > maxSize) {
            throw new Error(`File too large. Maximum size: ${maxSize / (1024 * 1024)}MB`);
        }
        
        if (!allowedTypes.some(type => file.type.startsWith(type.split('/')[0]))) {
            throw new Error(`Unsupported file type: ${file.type}`);
        }
    }
    
    /**
     * Upload video to server
     */
    async uploadVideo(file) {
        const formData = new FormData();
        formData.append('video', file);
        
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    }
    
    /**
     * Update video properties display
     */
    updateVideoProperties() {
        if (!this.videoProperties) {
            this.elements.properties.textContent = 'No video loaded';
            return;
        }
        
        const { fps, frames, width, height, duration, filename, codec } = this.videoProperties;
        
        this.elements.properties.innerHTML = `
            <strong>Video Properties:</strong><br>
            File: ${filename} | 
            Resolution: ${width}×${height} | 
            Duration: ${duration.toFixed(1)}s | 
            FPS: ${fps} | 
            Frames: ${frames} | 
            Codec: ${codec || 'Unknown'}
        `;
    }
    
    /**
     * Setup frame control elements
     */
    setupFrameControls() {
        if (!this.videoProperties) return;
        
        this.elements.frameSlider.max = this.videoProperties.frames - 1;
        this.elements.frameSlider.value = 0;
        this.elements.totalFramesSpan.textContent = this.videoProperties.frames.toLocaleString();
        this.elements.frameControls.style.display = 'block';
    }
    
    /**
     * Display a specific frame
     */
    async displayFrame(frameNum) {
        try {
            // Cancel any pending frame request
            this.frameRequestController.abort();
            this.frameRequestController = new AbortController();
            
            const response = await fetch(`/process_frame/${frameNum}`, {
                signal: this.frameRequestController.signal
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.frame) {
                this.elements.videoFrame.src = data.frame;
                this.elements.videoFrame.style.display = 'block';
                this.elements.videoPlaceholder.style.display = 'none';
                
                this.currentFrame = frameNum;
                this.updateFrameDisplay();
                
                // Clear any previous errors
                this.showError(null);
            }
        } catch (error) {
            if (error.name === 'AbortError') {
                // Request was cancelled, ignore
                return;
            }
            
            console.error('Frame display error:', error);
            this.showError(`Failed to load frame ${frameNum}: ${error.message}`);
        }
    }
    
    /**
     * Update frame number and progress display
     */
    updateFrameDisplay() {
        if (!this.videoProperties) return;
        
        this.elements.currentFrameSpan.textContent = this.currentFrame.toLocaleString();
        this.elements.frameSlider.value = this.currentFrame;
        
        const progress = (this.currentFrame / (this.videoProperties.frames - 1)) * 100;
        this.elements.progressBar.style.width = `${Math.max(0, Math.min(100, progress))}%`;
    }
    
    /**
     * Seek to a specific frame
     */
    async seekToFrame(frameNum) {
        if (!this.videoProperties) return;
        
        const clampedFrame = Math.max(0, Math.min(this.videoProperties.frames - 1, frameNum));
        await this.displayFrame(clampedFrame);
    }
    
    /**
     * Start video playback
     */
    async playVideo() {
        if (!this.videoProperties) return;
        
        this.isPlaying = true;
        this.updateUIState();
        
        const frameRate = Math.max(1, this.videoProperties.fps || 30);
        const frameDelay = 1000 / frameRate;
        
        this.playInterval = setInterval(async () => {
            if (!this.isPlaying) {
                this.pauseVideo();
                return;
            }
            
            if (this.currentFrame < this.videoProperties.frames - 1) {
                await this.displayFrame(this.currentFrame + 1);
            } else {
                this.pauseVideo();
            }
        }, frameDelay);
    }
    
    /**
     * Pause video playback
     */
    pauseVideo() {
        this.isPlaying = false;
        this.updateUIState();
        
        if (this.playInterval) {
            clearInterval(this.playInterval);
            this.playInterval = null;
        }
    }
    
    /**
     * Stop video playback and return to first frame
     */
    async stopVideo() {
        this.pauseVideo();
        await this.seekToFrame(0);
    }
    
    /**
     * Update UI state based on current video and playback state
     */
    updateUIState() {
        const hasVideo = Boolean(this.videoProperties);
        
        this.elements.playBtn.disabled = !hasVideo;
        this.elements.stopBtn.disabled = !hasVideo;
        this.elements.playBtn.textContent = this.isPlaying ? 'Pause' : 'Play';
        
        // Update play button appearance
        this.elements.playBtn.className = this.isPlaying 
            ? 'btn btn-warning' 
            : 'btn btn-secondary';
    }
    
    /**
     * Set loading state
     */
    setLoadingState(isLoading, message = 'Loading...') {
        if (this.elements.loadingIndicator) {
            this.elements.loadingIndicator.style.display = isLoading ? 'block' : 'none';
            this.elements.loadingIndicator.textContent = message;
        }
        
        // Disable controls during loading
        const controlButtons = [this.elements.selectBtn, this.elements.playBtn, this.elements.stopBtn];
        controlButtons.forEach(btn => {
            if (btn) btn.disabled = isLoading;
        });
    }
    
    /**
     * Show error message
     */
    showError(message) {
        if (this.elements.errorMessage) {
            this.elements.errorMessage.style.display = message ? 'block' : 'none';
            this.elements.errorMessage.textContent = message || '';
            
            if (message) {
                // Auto-hide error after 10 seconds
                setTimeout(() => this.showError(null), 10000);
            }
        } else if (message) {
            // Fallback to properties element
            this.elements.properties.textContent = `Error: ${message}`;
            this.elements.properties.style.backgroundColor = '#f8d7da';
            this.elements.properties.style.borderColor = '#f5c6cb';
            this.elements.properties.style.color = '#721c24';
        }
    }
    
    /**
     * Show success message
     */
    showSuccess(message) {
        // Temporarily show success in properties
        const originalBg = this.elements.properties.style.backgroundColor;
        const originalBorder = this.elements.properties.style.borderColor;
        const originalColor = this.elements.properties.style.color;
        
        this.elements.properties.style.backgroundColor = '#d4edda';
        this.elements.properties.style.borderColor = '#c3e6cb';
        this.elements.properties.style.color = '#155724';
        
        // Restore original styles after 3 seconds
        setTimeout(() => {
            this.elements.properties.style.backgroundColor = originalBg;
            this.elements.properties.style.borderColor = originalBorder;
            this.elements.properties.style.color = originalColor;
        }, 3000);
    }
    
    /**
     * Clean up resources
     */
    cleanup() {
        this.pauseVideo();
        this.frameRequestController.abort();
        
        // Clean up session on server
        fetch('/cleanup_session', { method: 'POST' })
            .catch(error => console.error('Cleanup error:', error));
    }
}

// Initialize video player when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.videoPlayer = new VideoPlayer();
});