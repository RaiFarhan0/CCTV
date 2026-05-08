document.addEventListener('DOMContentLoaded', () => {
    // Initialize components
    const alertPanel = new AlertPanel();
    const videoPlayer = new VideoPlayer();

    // Make them globally accessible for interactions
    window.alertPanel = alertPanel;
    window.videoPlayer = videoPlayer;

    // DOM Elements
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const uploadBtn = document.getElementById('upload-btn');
    const progressContainer = document.getElementById('progress-container');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const statusPill = document.getElementById('system-status');
    const liveClock = document.getElementById('live-clock');

    // Live Clock
    setInterval(() => {
        const now = new Date();
        liveClock.textContent = now.toLocaleTimeString('en-US', { hour12: false });
    }, 1000);

    // Socket.IO Connection
    // Determine backend URL (assuming it runs on same host, port 5000)
    const backendUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
        ? `http://${window.location.hostname}:5000`
        : '';

    const socket = io(backendUrl);

    socket.on('connect', () => {
        console.log('Connected to backend via Socket.IO');
        checkBackendStatus();
    });

    socket.on('processing_progress', (data) => {
        statusPill.textContent = 'Processing';
        statusPill.className = 'status-pill processing';

        progressContainer.classList.remove('hidden');
        progressFill.style.width = `${data.progress}%`;
        progressText.textContent = `${data.progress}%`;

        // Update stats
        document.getElementById('stat-frames').textContent = Math.floor((data.progress / 100) * 1000) + "+"; // Mock estimation
    });

    socket.on('alert_detected', (alert) => {
        console.log('New alert detected:', alert.type);
        alertPanel.addAlert(alert);
        videoPlayer.setAnomalies(alertPanel.alerts); // Update video player with new alerts
    });

    socket.on('processing_complete', (data) => {
        statusPill.textContent = 'Complete';
        statusPill.className = 'status-pill complete';

        progressFill.style.width = '100%';
        progressText.textContent = '100%';
        setTimeout(() => {
            progressContainer.classList.add('hidden');
        }, 3000);

        console.log('Processing complete. Fetching final video...');
        fetchAlertsAndVideo(data.filename);
    });

    socket.on('processing_error', (data) => {
        statusPill.textContent = 'Error';
        statusPill.className = 'status-pill critical-text';
        progressText.textContent = 'Failed';
        alert(`Processing error: ${data.error}`);
    });

    // Fetch initial state
    async function checkBackendStatus() {
        try {
            const res = await fetch(`${backendUrl}/status`);
            const data = await res.json();

            if (data.status === 'Processing') {
                statusPill.textContent = 'Processing';
                statusPill.className = 'status-pill processing';
                progressContainer.classList.remove('hidden');
            } else if (data.status === 'Complete' && data.filename) {
                statusPill.textContent = 'Complete';
                statusPill.className = 'status-pill complete';
                fetchAlertsAndVideo(data.filename);
            }
        } catch (e) {
            console.error('Error checking backend status:', e);
        }
    }

    async function fetchAlertsAndVideo(filename) {
        try {
            // Fetch all alerts
            const alertsRes = await fetch(`${backendUrl}/alerts`);
            const alerts = await alertsRes.json();

            alertPanel.clear();
            // Server returns chronological, we want newest first in feed
            alerts.forEach(a => alertPanel.addAlert(a));

            // Set video player data
            videoPlayer.setAnomalies(alerts);
            videoPlayer.loadVideo(`${backendUrl}/video/${filename}`);

        } catch (e) {
            console.error('Error fetching final data:', e);
        }
    }

    // File Upload Handling
    uploadBtn.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) handleUpload(e.target.files[0]);
    });

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) handleUpload(e.dataTransfer.files[0]);
    });

    async function handleUpload(file) {
        const allowed = ['video/mp4', 'video/avi', 'video/quicktime'];
        // fallback extension check if mime type is empty
        const ext = file.name.split('.').pop().toLowerCase();
        const validExt = ['mp4', 'avi', 'mov'].includes(ext);

        if (!allowed.includes(file.type) && !validExt) {
            alert('Invalid file type. Please upload MP4, AVI, or MOV.');
            return;
        }

        const formData = new FormData();
        formData.append('video', file);

        try {
            statusPill.textContent = 'Uploading...';
            statusPill.className = 'status-pill';

            // Clear previous state
            alertPanel.clear();
            videoPlayer.setAnomalies([]);
            document.getElementById('video-placeholder').style.display = 'flex';
            document.getElementById('cctv-video').style.display = 'none';

            const startTime = Date.now();

            // Start timer
            const timerInterval = setInterval(() => {
                const diff = Math.floor((Date.now() - startTime) / 1000);
                document.getElementById('stat-time').textContent = `${diff}s`;
            }, 1000);

            // Store interval ID globally to clear it later if needed (simplification)
            window.processingTimer = timerInterval;

            const res = await fetch(`${backendUrl}/upload`, {
                method: 'POST',
                body: formData
            });

            const data = await res.json();
            if (!res.ok) throw new Error(data.error || 'Upload failed');

            console.log('Upload successful, processing started:', data);

        } catch (e) {
            console.error('Upload error:', e);
            alert(`Upload error: ${e.message}`);
            statusPill.textContent = 'Error';
            statusPill.className = 'status-pill critical-text';
            clearInterval(window.processingTimer);
        }
    }
});