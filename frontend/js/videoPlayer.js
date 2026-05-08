class VideoPlayer {
    constructor() {
        this.video = document.getElementById('cctv-video');
        this.canvas = document.getElementById('overlay-canvas');
        this.ctx = this.canvas.getContext('2d');
        this.playPauseBtn = document.getElementById('play-pause-btn');
        this.timeDisplay = document.getElementById('video-time');
        this.seekBar = document.getElementById('seek-bar');
        this.speedSelector = document.getElementById('speed-selector');
        this.placeholder = document.getElementById('video-placeholder');
        this.timelineMarkers = document.getElementById('timeline-markers');
        this.jumpContainer = document.getElementById('jump-buttons-container');

        this.anomalies = [];
        this.fps = 30; // Assumption, can be updated later

        this.colors = {
            'CRITICAL': '#ff3b3b', // Red
            'HIGH': '#ffaa00',     // Orange
            'MEDIUM': '#ffff00',   // Yellow
            'LOW': '#00d4ff'       // Blue
        };

        this.bindEvents();
        this.resizeCanvas();
        window.addEventListener('resize', () => this.resizeCanvas());
    }

    bindEvents() {
        this.playPauseBtn.addEventListener('click', () => {
            if (this.video.paused || this.video.ended) {
                this.video.play();
            } else {
                this.video.pause();
            }
        });

        this.video.addEventListener('play', () => {
            this.playPauseBtn.innerHTML = '<svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" stroke-width="2" fill="none"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>';
            this.drawLoop();
        });

        this.video.addEventListener('pause', () => {
            this.playPauseBtn.innerHTML = '<svg viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" stroke-width="2" fill="none"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>';
        });

        this.video.addEventListener('timeupdate', () => {
            this.updateTimeDisplay();
            this.updateSeekBar();
            if (this.video.paused) {
                this.drawOverlays();
            }
        });

        this.video.addEventListener('loadedmetadata', () => {
            this.updateTimeDisplay();
            this.resizeCanvas();
        });

        this.seekBar.addEventListener('input', () => {
            const time = this.video.duration * (this.seekBar.value / 100);
            this.video.currentTime = time;
            if (this.video.paused) {
                this.drawOverlays();
            }
        });

        this.speedSelector.addEventListener('change', (e) => {
            this.video.playbackRate = parseFloat(e.target.value);
        });
    }

    loadVideo(url) {
        this.video.src = url;
        this.video.style.display = 'block';
        this.placeholder.style.display = 'none';
        this.video.load();
    }

    setAnomalies(alerts) {
        this.anomalies = alerts;
        this.createMarkers();
        this.createJumpButtons();
    }

    seek(timeInSeconds) {
        if (this.video.readyState > 0) {
            this.video.currentTime = timeInSeconds;
            // Play automatically for a better UX
            this.video.play().catch(e => console.log("Auto-play prevented", e));
        }
    }

    formatTime(seconds) {
        if (isNaN(seconds)) return "00:00";
        const m = Math.floor(seconds / 60).toString().padStart(2, '0');
        const s = Math.floor(seconds % 60).toString().padStart(2, '0');
        return `${m}:${s}`;
    }

    updateTimeDisplay() {
        this.timeDisplay.textContent = `${this.formatTime(this.video.currentTime)} / ${this.formatTime(this.video.duration)}`;
    }

    updateSeekBar() {
        if (this.video.duration) {
            const value = (100 / this.video.duration) * this.video.currentTime;
            this.seekBar.value = value;
        }
    }

    resizeCanvas() {
        // Match canvas logical size to video actual display size
        const rect = this.video.getBoundingClientRect();
        this.canvas.width = rect.width;
        this.canvas.height = rect.height;
    }

    createMarkers() {
        this.timelineMarkers.innerHTML = '';

        // Wait for metadata to know duration
        if (!this.video.duration || isNaN(this.video.duration)) {
            setTimeout(() => this.createMarkers(), 500);
            return;
        }

        this.anomalies.forEach(alert => {
            const timeInSeconds = alert.frame_number / this.fps;
            const percentage = (timeInSeconds / this.video.duration) * 100;

            if (percentage >= 0 && percentage <= 100) {
                const marker = document.createElement('div');
                marker.className = 'marker';
                marker.style.left = `${percentage}%`;
                marker.style.backgroundColor = this.colors[alert.severity];
                marker.setAttribute('data-tooltip', `${alert.type} (${alert.timestamp})`);

                marker.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.seek(timeInSeconds);
                });

                this.timelineMarkers.appendChild(marker);
            }
        });
    }

    createJumpButtons() {
        this.jumpContainer.innerHTML = '';

        this.anomalies.forEach(alert => {
            const btn = document.createElement('button');
            btn.className = 'jump-btn';
            btn.textContent = `${alert.type} @ ${alert.timestamp}`;
            btn.style.borderLeft = `2px solid ${this.colors[alert.severity]}`;

            btn.addEventListener('click', () => {
                const timeInSeconds = alert.frame_number / this.fps;
                this.seek(timeInSeconds);
            });

            this.jumpContainer.appendChild(btn);
        });
    }

    drawLoop() {
        if (!this.video.paused && !this.video.ended) {
            this.drawOverlays();
            requestAnimationFrame(() => this.drawLoop());
        }
    }

    drawOverlays() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Find anomalies near current time (within 0.5s window)
        const currentTime = this.video.currentTime;
        const windowSize = 0.5; // seconds

        // We need to scale bounding boxes from original video resolution to canvas resolution
        const videoWidth = this.video.videoWidth;
        const videoHeight = this.video.videoHeight;

        if (!videoWidth || !videoHeight) return;

        // Calculate letterboxing/pillarboxing offsets and scales
        const canvasRatio = this.canvas.width / this.canvas.height;
        const videoRatio = videoWidth / videoHeight;

        let drawWidth, drawHeight, offsetX = 0, offsetY = 0;

        if (canvasRatio > videoRatio) {
            // Pillarbox
            drawHeight = this.canvas.height;
            drawWidth = drawHeight * videoRatio;
            offsetX = (this.canvas.width - drawWidth) / 2;
        } else {
            // Letterbox
            drawWidth = this.canvas.width;
            drawHeight = drawWidth / videoRatio;
            offsetY = (this.canvas.height - drawHeight) / 2;
        }

        const scaleX = drawWidth / videoWidth;
        const scaleY = drawHeight / videoHeight;

        const activeAlerts = this.anomalies.filter(a => {
            const aTime = a.frame_number / this.fps;
            return Math.abs(aTime - currentTime) < windowSize;
        });

        activeAlerts.forEach(alert => {
            this.ctx.strokeStyle = this.colors[alert.severity];
            this.ctx.lineWidth = 2;

            // Fade in effect based on distance to exact time
            const aTime = alert.frame_number / this.fps;
            const diff = Math.abs(aTime - currentTime);
            const alpha = Math.max(0, 1 - (diff / windowSize));

            this.ctx.globalAlpha = alpha;

            if (alert.bbox) {
                // Exact bounding box mapping
                const [bx1, by1, bx2, by2] = alert.bbox;
                const rectX = offsetX + (bx1 * scaleX);
                const rectY = offsetY + (by1 * scaleY);
                const rectW = (bx2 - bx1) * scaleX;
                const rectH = (by2 - by1) * scaleY;

                this.ctx.strokeRect(rectX, rectY, rectW, rectH);

                // Draw label
                this.ctx.fillStyle = this.colors[alert.severity];
                this.ctx.font = '14px "Orbitron", sans-serif';
                this.ctx.fillText(`${alert.type} (${(alert.confidence*100).toFixed(0)}%)`, rectX, rectY - 5);
            } else {
                // Fallback UI indicator if bbox is missing
                const padding = 20;
                const len = 40;
                const w = this.canvas.width;
                const h = this.canvas.height;

                this.ctx.beginPath();
                // Top Left
                this.ctx.moveTo(padding, padding + len);
                this.ctx.lineTo(padding, padding);
                this.ctx.lineTo(padding + len, padding);
                // Top Right
                this.ctx.moveTo(w - padding - len, padding);
                this.ctx.lineTo(w - padding, padding);
                this.ctx.lineTo(w - padding, padding + len);
                // Bottom Right
                this.ctx.moveTo(w - padding, h - padding - len);
                this.ctx.lineTo(w - padding, h - padding);
                this.ctx.lineTo(w - padding - len, h - padding);
                // Bottom Left
                this.ctx.moveTo(padding + len, h - padding);
                this.ctx.lineTo(padding, h - padding);
                this.ctx.lineTo(padding, h - padding - len);

                this.ctx.stroke();

                this.ctx.fillStyle = this.colors[alert.severity];
                this.ctx.font = '16px "Orbitron", sans-serif';
                this.ctx.fillText(`DETECTED: ${alert.type} (${(alert.confidence*100).toFixed(0)}%)`, padding + 10, padding + 30);
            }

            this.ctx.globalAlpha = 1.0;
        });
    }
}