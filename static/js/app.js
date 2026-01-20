/**
 * Google Maps Closed Places Manager - Main JavaScript
 */

// Utility functions
const Utils = {
    /**
     * Escape HTML special characters
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Format a date for display
     */
    formatDate(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleString();
    },

    /**
     * Format business status for display
     */
    formatStatus(status) {
        if (!status) return 'Unknown';
        return status.replace(/_/g, ' ').toLowerCase()
            .replace(/\b\w/g, c => c.toUpperCase());
    },

    /**
     * Sleep for a specified number of milliseconds
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    },

    /**
     * Show an element
     */
    show(element) {
        if (element) {
            element.classList.remove('hidden');
        }
    },

    /**
     * Hide an element
     */
    hide(element) {
        if (element) {
            element.classList.add('hidden');
        }
    },

    /**
     * Toggle element visibility
     */
    toggle(element, show) {
        if (element) {
            element.classList.toggle('hidden', !show);
        }
    }
};

// API client
const API = {
    /**
     * Make a GET request
     */
    async get(url) {
        const response = await fetch(url);
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        return response.json();
    },

    /**
     * Make a POST request
     */
    async post(url, data) {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        return response.json();
    },

    /**
     * Upload a file
     */
    async uploadFile(url, file) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(url, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        return response.json();
    }
};

// WebSocket helper
class ProgressWebSocket {
    constructor(jobId, callbacks = {}) {
        this.jobId = jobId;
        this.callbacks = callbacks;
        this.socket = null;
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${window.location.host}/ws/progress/${this.jobId}`;

        this.socket = new WebSocket(url);

        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);

            if (data.error && this.callbacks.onError) {
                this.callbacks.onError(data.error);
                return;
            }

            if (this.callbacks.onProgress) {
                this.callbacks.onProgress(data.progress);
            }

            if (data.status === 'completed' && this.callbacks.onComplete) {
                this.callbacks.onComplete(data.result);
            } else if (data.status === 'failed' && this.callbacks.onError) {
                this.callbacks.onError(data.error);
            }
        };

        this.socket.onerror = (error) => {
            if (this.callbacks.onError) {
                this.callbacks.onError('WebSocket connection error');
            }
        };

        this.socket.onclose = () => {
            if (this.callbacks.onClose) {
                this.callbacks.onClose();
            }
        };
    }

    disconnect() {
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
    }
}

// Progress bar helper
class ProgressBar {
    constructor(barElement, statusElement) {
        this.bar = barElement;
        this.status = statusElement;
    }

    update(percentage, message) {
        if (this.bar) {
            this.bar.style.width = `${percentage}%`;
        }
        if (this.status && message) {
            this.status.textContent = message;
        }
    }

    reset() {
        this.update(0, '');
    }
}

// Export for use in templates
window.Utils = Utils;
window.API = API;
window.ProgressWebSocket = ProgressWebSocket;
window.ProgressBar = ProgressBar;
