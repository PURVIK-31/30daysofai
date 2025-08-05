// 30 Days of AI - Day 1: Project Setup
// Minimalistic frontend JavaScript

class App {
    constructor() {
        this.baseUrl = window.location.origin;
        this.init();
    }

    async init() {
        await this.checkBackendStatus();
        await this.loadDayInfo();
    }

    async checkBackendStatus() {
        const statusIndicator = document.getElementById('status-indicator');
        const statusDot = statusIndicator.querySelector('.status-dot');
        const statusText = statusIndicator.querySelector('.status-text');

        try {
            const response = await fetch(`${this.baseUrl}/api/health`);
            const data = await response.json();

            if (response.ok) {
                statusDot.classList.remove('error');
                statusDot.classList.add('healthy');
                statusText.textContent = 'Backend is running';
            } else {
                throw new Error('Backend responded with error');
            }
        } catch (error) {
            statusDot.classList.remove('healthy');
            statusDot.classList.add('error');
            statusText.textContent = 'Backend connection failed';
        }
    }

    async loadDayInfo() {
        const dayInfo = document.getElementById('day-info');

        try {
            const response = await fetch(`${this.baseUrl}/api/day`);
            const data = await response.json();

            if (response.ok) {
                dayInfo.innerHTML = `
                    <p><strong>Day ${data.day}:</strong> ${data.title}</p>
                `;
            } else {
                throw new Error('Failed to load day info');
            }
        } catch (error) {
            dayInfo.innerHTML = `
                <p>Could not load project information</p>
            `;
        }
        this.initTTS();
    }

    initTTS() {
        const input = document.getElementById('tts-input');
        const button = document.getElementById('tts-submit');
        const audioEl = document.getElementById('tts-audio');

        if (!input || !button || !audioEl) return; // elements not present

        button.addEventListener('click', async () => {
            const text = input.value.trim();
            if (!text) {
                alert('Please enter some text!');
                return;
            }

            button.disabled = true;
            button.textContent = 'Generating...';

            try {
                const resp = await fetch(`${this.baseUrl}/api/tts/generate`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ text })
                });

                const data = await resp.json();
                if (!resp.ok || !data.success) {
                    let errorMsg = data.detail || data.message || 'TTS generation failed';
                    if (data.raw_response) {
                        errorMsg += ` (Server response: ${JSON.stringify(data.raw_response)})`;
                    }
                    throw new Error(errorMsg);
                }

                audioEl.src = data.audio_url;
                audioEl.style.display = 'block';
                await audioEl.play();
            } catch (err) {
                console.error(err);
                alert('Error: ' + err.message);
            } finally {
                button.disabled = false;
                button.textContent = 'Generate Audio';
            }
        });
        this.initEchoBot();
    }

    initEchoBot() {
        const startButton = document.getElementById('start-recording');
        const stopButton = document.getElementById('stop-recording');
        const audioEl = document.getElementById('echo-audio');

        if (!startButton || !stopButton || !audioEl) return; // elements not present

        let mediaRecorder = null;
        let audioChunks = [];

        startButton.addEventListener('click', async () => {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];

                mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) {
                        audioChunks.push(event.data);
                    }
                };

                mediaRecorder.onstop = () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                    const audioUrl = URL.createObjectURL(audioBlob);
                    audioEl.src = audioUrl;
                    audioEl.style.display = 'block';
                    audioEl.play().catch(err => console.error('Playback failed:', err));
                    // Stop all tracks to release microphone
                    stream.getTracks().forEach(track => track.stop());
                };

                mediaRecorder.start();
                startButton.disabled = true;
                stopButton.disabled = false;
            } catch (err) {
                console.error('Failed to start recording:', err);
                alert('Could not start recording: ' + err.message);
            }
        });

        stopButton.addEventListener('click', () => {
            if (mediaRecorder && mediaRecorder.state === 'recording') {
                mediaRecorder.stop();
                startButton.disabled = false;
                stopButton.disabled = true;
            }
        });
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new App();
}); 