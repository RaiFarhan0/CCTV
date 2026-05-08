class AlertPanel {
    constructor() {
        this.feed = document.getElementById('alert-feed');
        this.badge = document.getElementById('alert-badge');
        this.totalStat = document.getElementById('stat-total-alerts');
        this.highStat = document.getElementById('stat-high-severity');
        this.filterTabs = document.getElementById('filter-tabs');

        this.alerts = [];
        this.currentFilter = 'ALL';
        this.audioContext = null;

        this.setupFilters();
    }

    initAudio() {
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
    }

    playBeep() {
        try {
            this.initAudio();
            if (this.audioContext.state === 'suspended') {
                this.audioContext.resume();
            }

            const oscillator = this.audioContext.createOscillator();
            const gainNode = this.audioContext.createGain();

            oscillator.type = 'square';
            oscillator.frequency.setValueAtTime(880, this.audioContext.currentTime); // A5
            oscillator.frequency.exponentialRampToValueAtTime(440, this.audioContext.currentTime + 0.1);

            gainNode.gain.setValueAtTime(0.1, this.audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.001, this.audioContext.currentTime + 0.3);

            oscillator.connect(gainNode);
            gainNode.connect(this.audioContext.destination);

            oscillator.start();
            oscillator.stop(this.audioContext.currentTime + 0.3);
        } catch (e) {
            console.log("Audio playback blocked by browser policy");
        }
    }

    setupFilters() {
        this.filterTabs.addEventListener('click', (e) => {
            if (e.target.classList.contains('filter-tab')) {
                // Update active class
                this.filterTabs.querySelectorAll('.filter-tab').forEach(tab => {
                    tab.classList.remove('active');
                });
                e.target.classList.add('active');

                // Filter alerts
                this.currentFilter = e.target.getAttribute('data-filter');
                this.renderFeed();
            }
        });
    }

    addAlert(alertData) {
        this.alerts.unshift(alertData); // Add to beginning
        this.updateStats();

        if (alertData.severity === 'CRITICAL' || alertData.severity === 'HIGH') {
            this.playBeep();
        }

        if (this.currentFilter === 'ALL' || this.currentFilter === alertData.severity) {
            const card = this.createAlertCard(alertData);
            this.feed.prepend(card);
        }
    }

    updateStats() {
        this.badge.textContent = this.alerts.length;
        this.totalStat.textContent = this.alerts.length;

        const highCount = this.alerts.filter(a => a.severity === 'CRITICAL' || a.severity === 'HIGH').length;
        this.highStat.textContent = highCount;
    }

    createAlertCard(alert) {
        const card = document.createElement('div');
        card.className = `alert-card severity-${alert.severity}`;
        card.setAttribute('data-id', alert.id);

        const img = document.createElement('img');
        img.className = 'alert-thumb';
        img.src = `data:image/jpeg;base64,${alert.thumbnail}`;
        img.alt = 'Anomaly Frame';

        const info = document.createElement('div');
        info.className = 'alert-info';

        const topRow = document.createElement('div');
        topRow.style.display = 'flex';
        topRow.style.justifyContent = 'space-between';

        const type = document.createElement('span');
        type.className = 'alert-type';
        type.textContent = alert.type;

        const time = document.createElement('span');
        time.className = 'alert-time';
        time.textContent = alert.timestamp;

        topRow.appendChild(type);
        topRow.appendChild(time);

        const descRow = document.createElement('div');
        descRow.className = 'alert-time'; // Reuse muted style
        descRow.style.marginTop = '4px';
        descRow.textContent = alert.description;

        const confBar = document.createElement('div');
        confBar.className = 'alert-conf-bar';

        const confFill = document.createElement('div');
        confFill.className = 'alert-conf-fill';
        confFill.style.width = `${alert.confidence * 100}%`;

        confBar.appendChild(confFill);

        info.appendChild(topRow);
        info.appendChild(descRow);
        info.appendChild(confBar);

        card.appendChild(img);
        card.appendChild(info);

        // Add click listener to seek video
        card.style.cursor = 'pointer';
        card.addEventListener('click', () => {
            if (window.videoPlayer) {
                // Approximate time based on 30fps assumption if we don't have exact time
                const timeInSeconds = alert.frame_number / 30;
                window.videoPlayer.seek(timeInSeconds);
            }
        });

        return card;
    }

    renderFeed() {
        this.feed.innerHTML = '';

        const filteredAlerts = this.currentFilter === 'ALL'
            ? this.alerts
            : this.alerts.filter(a => a.severity === this.currentFilter);

        filteredAlerts.forEach(alert => {
            this.feed.appendChild(this.createAlertCard(alert));
        });
    }

    clear() {
        this.alerts = [];
        this.renderFeed();
        this.updateStats();
    }
}
