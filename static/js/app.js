// 30 Days of AI - Day 1: Project Setup
// Minimalistic frontend JavaScript

class App {
    constructor() {
        this.baseUrl = window.location.origin;
        this.sessionId = this.ensureSessionId();
        this.currentPersona = null;
        this.personas = {};
        this.simulateCreditExhaustion = false;
        this.init();
    }

    async init() {
        await this.checkBackendStatus();
        await this.loadDayInfo();
        await this.loadPersonas();
        await this.loadCurrentPersona();
        this.bindNewSession();
        this.initSettingsUI();
    }

    async checkBackendStatus() {
        const statusIndicator = document.getElementById('status-indicator');
        const statusDot = statusIndicator.querySelector('.status-dot');
        const statusText = statusIndicator.querySelector('.status-text');
        const sessionInfo = document.getElementById('session-info');

        try {
            const response = await fetch(`${this.baseUrl}/api/health`);
            const data = await response.json();

            if (response.ok) {
                statusDot.classList.remove('error');
                statusDot.classList.add('healthy');
                statusText.textContent = 'Backend is running';
                if (sessionInfo) sessionInfo.textContent = `Session: ${this.sessionId}`;
            } else {
                throw new Error('Backend responded with error');
            }
        } catch (error) {
            statusDot.classList.remove('healthy');
            statusDot.classList.add('error');
            statusText.textContent = 'Backend connection failed';
            if (sessionInfo) sessionInfo.textContent = `Session: ${this.sessionId}`;
        }
    }

    initSettingsUI() {
        const openBtn = document.getElementById('open-settings');
        const closeBtn = document.getElementById('close-settings');
        const saveBtn = document.getElementById('save-settings');
        const modal = document.getElementById('settings-modal');
        if (!openBtn || !closeBtn || !saveBtn || !modal) return;

        const keyGemini = document.getElementById('key-gemini');
        const keyAAI = document.getElementById('key-assemblyai');
        const keyMurf = document.getElementById('key-murf');
        const keyTavily = document.getElementById('key-tavily');
        const modelGemini = document.getElementById('model-gemini');
        const murfVoiceId = document.getElementById('murf-voice-id');

        const loadLocal = () => {
            try {
                const raw = localStorage.getItem('userKeys');
                if (!raw) return;
                const parsed = JSON.parse(raw);
                if (parsed.GEMINI_API_KEY && keyGemini) keyGemini.value = parsed.GEMINI_API_KEY;
                if (parsed.ASSEMBLYAI_API_KEY && keyAAI) keyAAI.value = parsed.ASSEMBLYAI_API_KEY;
                if (parsed.MURF_API_KEY && keyMurf) keyMurf.value = parsed.MURF_API_KEY;
                if (parsed.TAVILY_API_KEY && keyTavily) keyTavily.value = parsed.TAVILY_API_KEY;
                if (parsed.GEMINI_MODEL && modelGemini) modelGemini.value = parsed.GEMINI_MODEL;
                if (parsed.MURF_VOICE_ID && murfVoiceId) murfVoiceId.value = parsed.MURF_VOICE_ID;
            } catch (_) {}
        };

        const fetchServerConfig = async () => {
            try {
                const res = await fetch(`${this.baseUrl}/api/config/${encodeURIComponent(this.sessionId)}/keys`);
                const data = await res.json();
                if (data && data.model && modelGemini && !modelGemini.value) modelGemini.value = data.model;
                if (data && data.murf_voice_id && murfVoiceId && !murfVoiceId.value) murfVoiceId.value = data.murf_voice_id;
            } catch (_) {}
        };

        const open = async () => {
            loadLocal();
            await fetchServerConfig();
            modal.style.display = 'flex';
        };
        const close = () => { modal.style.display = 'none'; };

        openBtn.addEventListener('click', open);
        closeBtn.addEventListener('click', close);
        modal.addEventListener('click', (e) => { if (e.target === modal) close(); });

        saveBtn.addEventListener('click', async () => {
            const keys = {};
            if (keyGemini && keyGemini.value.trim()) keys['GEMINI_API_KEY'] = keyGemini.value.trim();
            if (keyAAI && keyAAI.value.trim()) keys['ASSEMBLYAI_API_KEY'] = keyAAI.value.trim();
            if (keyMurf && keyMurf.value.trim()) keys['MURF_API_KEY'] = keyMurf.value.trim();
            if (keyTavily && keyTavily.value.trim()) keys['TAVILY_API_KEY'] = keyTavily.value.trim();
            if (modelGemini && modelGemini.value.trim()) keys['GEMINI_MODEL'] = modelGemini.value.trim();
            if (murfVoiceId && murfVoiceId.value.trim()) keys['MURF_VOICE_ID'] = murfVoiceId.value.trim();

            // Persist locally for convenience
            try { localStorage.setItem('userKeys', JSON.stringify(keys)); } catch (_) {}

            // Send to server for this session
            try {
                const res = await fetch(`${this.baseUrl}/api/config/${encodeURIComponent(this.sessionId)}/keys`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ keys })
                });
                const data = await res.json();
                if (!res.ok || !data.success) throw new Error('Failed to save settings');
                close();
                alert('Settings saved for this session.');
            } catch (err) {
                alert('Failed to save settings: ' + (err && err.message ? err.message : 'Unknown error'));
            }
        });
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
        await this.renderChatHistory();
        this.initAgentRecorder();
    }

    async loadPersonas() {
        try {
            const response = await fetch(`${this.baseUrl}/api/personas`);
            const data = await response.json();

            if (response.ok && data.personas) {
                this.personas = data.personas;
                this.renderPersonaGrid();
            } else {
                throw new Error('Failed to load personas');
            }
        } catch (error) {
            console.error('Error loading personas:', error);
            const grid = document.getElementById('persona-grid');
            if (grid) grid.innerHTML = '<p>Failed to load personas</p>';
        }
    }

    async loadCurrentPersona() {
        try {
            const response = await fetch(`${this.baseUrl}/api/personas/${encodeURIComponent(this.sessionId)}`);
            const data = await response.json();

            if (response.ok && data.persona) {
                this.currentPersona = data;
                this.updateCurrentPersonaDisplay();
                this.updatePersonaSelection(data.persona_id);
            }
        } catch (error) {
            console.error('Error loading current persona:', error);
        }
    }

    renderPersonaGrid() {
        const grid = document.getElementById('persona-grid');
        if (!grid || !this.personas) return;

        const personaCards = Object.entries(this.personas).map(([id, persona]) => {
            return `
                <div class="persona-card" data-persona-id="${id}">
                    <span class="persona-avatar">${persona.avatar}</span>
                    <div class="persona-name">${persona.name}</div>
                    <div class="persona-desc">${persona.description}</div>
                </div>
            `;
        }).join('');

        grid.innerHTML = personaCards;

        // Add click handlers
        grid.querySelectorAll('.persona-card').forEach(card => {
            card.addEventListener('click', async () => {
                const personaId = card.dataset.personaId;
                await this.selectPersona(personaId);
            });
        });
    }

    async selectPersona(personaId) {
        try {
            const response = await fetch(`${this.baseUrl}/api/personas/${encodeURIComponent(this.sessionId)}/${personaId}`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                this.currentPersona = data;
                this.updateCurrentPersonaDisplay();
                this.updatePersonaSelection(personaId);
                
                // Clear chat history when switching personas
                await this.clearChatHistory();
                await this.renderChatHistory();
                
                // Show success message
                const statusEl = document.getElementById('record-status');
                if (statusEl) {
                    statusEl.textContent = `Switched to ${data.persona.name}! Try speaking to them.`;
                    setTimeout(() => {
                        statusEl.textContent = 'Tap to speak';
                    }, 3000);
                }
            } else {
                throw new Error(data.detail || 'Failed to set persona');
            }
        } catch (error) {
            console.error('Error selecting persona:', error);
            alert(`Failed to select persona: ${error.message}`);
        }
    }

    updateCurrentPersonaDisplay() {
        if (!this.currentPersona) return;
        
        const currentPersonaEl = document.getElementById('current-persona');
        if (currentPersonaEl) {
            const persona = this.currentPersona.persona;
            currentPersonaEl.innerHTML = `
                <span class="persona-avatar">${persona.avatar}</span>
                <div class="persona-info">
                    <strong>${persona.name}</strong>
                    <p>${persona.description}</p>
                </div>
            `;
        }
    }

    updatePersonaSelection(selectedId) {
        const grid = document.getElementById('persona-grid');
        if (!grid) return;

        // Remove selected class from all cards
        grid.querySelectorAll('.persona-card').forEach(card => {
            card.classList.remove('selected');
        });

        // Add selected class to current persona
        const selectedCard = grid.querySelector(`[data-persona-id="${selectedId}"]`);
        if (selectedCard) {
            selectedCard.classList.add('selected');
        }
    }

    async clearChatHistory() {
        try {
            // We don't have a clear endpoint, but we can create a new session
            this.sessionId = this.generateSessionId();
            try { localStorage.setItem('sessionId', this.sessionId); } catch (_) {}
            const url = new URL(window.location.href);
            url.searchParams.set('session', this.sessionId);
            window.history.replaceState({}, '', url.toString());
            const sessionInfo = document.getElementById('session-info');
            if (sessionInfo) sessionInfo.textContent = `Session: ${this.sessionId}`;
        } catch (error) {
            console.error('Error clearing chat history:', error);
        }
    }

    initAgentRecorder() {
        const toggleBtn = document.getElementById('record-toggle');
        const audioEl = document.getElementById('agent-audio');
        const statusEl = document.getElementById('record-status');
        if (!toggleBtn || !audioEl || !statusEl) return;

        let mediaRecorder = null;
        let streamRef = null;
        let ws = null;
        const wsAudioUrl = this.baseUrl.replace(/^http/, 'ws') + '/ws/audio';
        const wsTranscribeUrl = this.baseUrl.replace(/^http/, 'ws') + '/ws/transcribe';
        let captureAudioContext = null;
        let processor = null;
        let sourceNode = null;
        let useTranscription = true; // Day 17: route to /ws/transcribe
        let forceHttpPipeline = false; // Day 23: fallback when WS streaming fails (SSL, etc.)
        let fallbackTimerId = null; // Day 23: auto-stop timer for non-streaming path

        let isListening = false;
        const appRef = this;

        const setListeningUI = (listening) => {
            isListening = listening;
            const label = toggleBtn.querySelector('.label');
            if (listening) {
                label.textContent = 'Stop';
                statusEl.textContent = 'Listening...';
                document.body.classList.add('recording');
            } else {
                label.textContent = 'Start';
                document.body.classList.remove('recording');
            }
        };

        const startRecording = async () => {
            try {
                streamRef = await navigator.mediaDevices.getUserMedia({ audio: true });
                if (useTranscription && !forceHttpPipeline) {
                    // Include session id in WS URL for server-side history persistence
                    const wsTranscribeSessionUrl = wsTranscribeUrl + `?session=${encodeURIComponent(this.sessionId)}`;
                    ws = new WebSocket(wsTranscribeSessionUrl);
                    ws.binaryType = 'arraybuffer';
                }

                if (useTranscription && !forceHttpPipeline && ws) ws.onopen = async () => {
                    if (useTranscription && !forceHttpPipeline) {
                        // WebAudio path: capture float32 at device rate, downsample to 16kHz, convert to PCM16 mono, send raw bytes
                        captureAudioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 48000 });
                        sourceNode = captureAudioContext.createMediaStreamSource(streamRef);
                        const desiredSampleRate = 16000;

                        const bufferSize = 2048;
                        processor = captureAudioContext.createScriptProcessor(bufferSize, 1, 1);

                        processor.onaudioprocess = (e) => {
                            if (!ws || ws.readyState !== WebSocket.OPEN) return;
                            const input = e.inputBuffer.getChannelData(0); // Float32 [-1,1]
                            const deviceRate = captureAudioContext.sampleRate;

                            // Downsample to 16kHz
                            const downsampled = downsampleBuffer(input, deviceRate, desiredSampleRate);
                            // Convert to 16-bit PCM
                            const pcm = floatTo16BitPCM(downsampled);
                            ws.send(pcm.buffer);
                        };

                        sourceNode.connect(processor);
                        processor.connect(captureAudioContext.destination);

                        statusEl.textContent = 'Streaming PCM audio for transcription...';
                        setListeningUI(true);
                    }
                };

                // Non-streaming HTTP fallback path
                if (!useTranscription || forceHttpPipeline) {
                    let chunks = [];
                    try {
                        mediaRecorder = new MediaRecorder(streamRef, { mimeType: 'audio/webm;codecs=opus' });
                    } catch (_) {
                        mediaRecorder = new MediaRecorder(streamRef);
                    }
                    mediaRecorder.ondataavailable = (event) => {
                        if (event.data && event.data.size > 0) {
                            chunks.push(event.data);
                        }
                    };
                    mediaRecorder.onstart = () => {
                        statusEl.textContent = 'Recording (non-streaming)...';
                        setListeningUI(true);
                        // Auto-stop after 6s so users don't have to press Stop
                        try { if (fallbackTimerId) clearTimeout(fallbackTimerId); } catch (_) {}
                        fallbackTimerId = setTimeout(() => {
                            try { if (mediaRecorder && mediaRecorder.state === 'recording') mediaRecorder.stop(); } catch (_) {}
                        }, 6000);
                    };
                    mediaRecorder.onstop = async () => {
                        try { if (fallbackTimerId) clearTimeout(fallbackTimerId); } catch (_) {}
                        fallbackTimerId = null;
                        try {
                            const blob = new Blob(chunks, { type: 'audio/webm' });
                            chunks = [];
                            statusEl.textContent = 'Processing: transcribing → LLM → TTS...';
                            await this.voiceLLMQuery(blob, audioEl, toggleBtn);
                        } catch (err) {
                            console.error('Fallback pipeline failed:', err);
                            statusEl.textContent = 'Fallback pipeline failed.';
                        } finally {
                            setListeningUI(false);
                        }
                    };
                    mediaRecorder.start();
                    // No websocket in this path
                }

                // Day 21: Audio streaming variables
                let audioChunks = [];
                let audioChunkCount = 0;
                
                // Day 22: Audio playback variables
                let playbackAudioContext = null;
                let audioQueue = [];
                let isPlaying = false;
                let nextStartTime = 0;
                
                // Day 22: Initialize Web Audio API
                const initializeAudioContext = () => {
                    if (!playbackAudioContext) {
                        playbackAudioContext = new (window.AudioContext || window.webkitAudioContext)();
                        nextStartTime = playbackAudioContext.currentTime;
                        console.log('[CLIENT] 🎵 Audio context initialized for streaming playback');
                    }
                };
                
                // Day 22: Convert base64 to ArrayBuffer
                const base64ToArrayBuffer = (base64) => {
                    try {
                        const binaryString = atob(base64);
                        const len = binaryString.length;
                        const bytes = new Uint8Array(len);
                        for (let i = 0; i < len; i++) {
                            bytes[i] = binaryString.charCodeAt(i);
                        }
                        return bytes.buffer;
                    } catch (error) {
                        console.error('[CLIENT] ❌ Error converting base64 to ArrayBuffer:', error);
                        return null;
                    }
                };
                
                // Day 22: Play audio chunk seamlessly
                const playAudioChunk = async (base64AudioChunk) => {
                    try {
                        initializeAudioContext();
                        
                        // Convert base64 to ArrayBuffer
                        const arrayBuffer = base64ToArrayBuffer(base64AudioChunk);
                        if (!arrayBuffer) return;
                        
                        // Decode audio data
                        const audioBuffer = await playbackAudioContext.decodeAudioData(arrayBuffer);
                        
                        // Create buffer source
                        const source = playbackAudioContext.createBufferSource();
                        source.buffer = audioBuffer;
                        source.connect(playbackAudioContext.destination);
                        
                        // Schedule playback for seamless streaming
                        const startTime = Math.max(playbackAudioContext.currentTime, nextStartTime);
                        source.start(startTime);
                        nextStartTime = startTime + audioBuffer.duration;
                        
                        console.log(`[CLIENT] 🎵 Playing audio chunk (duration: ${audioBuffer.duration.toFixed(2)}s, scheduled at: ${startTime.toFixed(2)}s)`);
                        
                        // Update playing status
                        if (!isPlaying) {
                            isPlaying = true;
                            statusEl.textContent = 'Playing streaming audio...';
                        }
                        
                        // Handle playback end
                        source.onended = () => {
                            // Check if this was the last scheduled chunk
                            if (playbackAudioContext.currentTime >= nextStartTime - 0.1) {
                                isPlaying = false;
                                console.log('[CLIENT] 🎵 Audio playback completed');
                            }
                        };
                        
                    } catch (error) {
                        console.error('[CLIENT] ❌ Error playing audio chunk:', error);
                        // Fallback: try to resume audio context if suspended
                        if (playbackAudioContext && playbackAudioContext.state === 'suspended') {
                            playbackAudioContext.resume().then(() => {
                                console.log('[CLIENT] 🎵 Audio context resumed');
                            });
                        }
                    }
                };
                
                if (useTranscription && !forceHttpPipeline && ws) ws.onmessage = (ev) => {
                    if (typeof ev.data !== 'string') return;
                    if (ev.data.startsWith('saved:')) {
                        const name = ev.data.slice('saved:'.length);
                        statusEl.textContent = `Saved as ${name}`;
                    } else if (ev.data.startsWith('partial:')) {
                        const text = ev.data.slice('partial:'.length);
                        statusEl.textContent = text;
                    } else if (ev.data.startsWith('final:')) {
                        const text = ev.data.slice('final:'.length);
                        statusEl.textContent = text;
                        // show final transcript above
                        try {
                            const container = document.getElementById('chat-history');
                            if (container) {
                                const safe = (text || '').replace(/&/g, '&amp;').replace(/</g, '&lt;');
                                const el = document.createElement('div');
                                el.className = 'message user';
                                el.innerHTML = `<div class="avatar user">U</div><div class="bubble">${safe}</div>`;
                                container.appendChild(el);
                                container.scrollTop = container.scrollHeight;
                            }
                        } catch (_) {}
                    } else if (ev.data.startsWith('turn_end:')) {
                        // Day 18: Explicit end-of-turn signal with final transcript
                        const text = ev.data.slice('turn_end:'.length);
                        statusEl.textContent = text;
                        // Stop capturing audio but keep WS open to receive TTS audio stream
                        try { if (processor) processor.disconnect(); } catch (_) {}
                        try { if (sourceNode) sourceNode.disconnect(); } catch (_) {}
                        try { if (captureAudioContext && captureAudioContext.state !== 'closed') captureAudioContext.close(); } catch (_) {}
                        // Do NOT close ws here; server will stream audio over the same socket
                        setListeningUI(false);
                        // Refresh chat early so user can see text even if TTS fails
                        try { appRef.renderChatHistory(); } catch (_) {}
                    } else if (ev.data.startsWith('error:')) {
                        const msg = ev.data.slice('error:'.length);
                        statusEl.textContent = `Error: ${msg}`;
                        // Auto-fallback on connect failures or missing SDK
                        if (msg.startsWith('connect_failed') || msg.includes('Universal Streaming API')) {
                            forceHttpPipeline = true;
                            try { if (processor) processor.disconnect(); } catch (_) {}
                            try { if (sourceNode) sourceNode.disconnect(); } catch (_) {}
                            try { if (captureAudioContext && captureAudioContext.state !== 'closed') captureAudioContext.close(); } catch (_) {}
                            try { if (ws) ws.close(); } catch (_) {}
                            statusEl.textContent = 'Streaming unavailable. Falling back to non-streaming flow...';
                            // Restart recording in fallback mode automatically
                            setListeningUI(false);
                            setTimeout(() => { if (!isListening) startRecording(); }, 250);
                        }
                    }
                    // Day 21: Handle audio streaming messages
                    else if (ev.data.startsWith('audio_start:')) {
                        const msg = ev.data.slice('audio_start:'.length);
                        statusEl.textContent = msg;
                        audioChunks = []; // Reset audio chunks array
                        audioChunkCount = 0;
                        console.log('[CLIENT] 🎵 Audio streaming started');
                    } else if (ev.data.startsWith('audio_status:')) {
                        const msg = ev.data.slice('audio_status:'.length);
                        statusEl.textContent = msg;
                        console.log(`[CLIENT] 📡 Audio status: ${msg}`);
                    } else if (ev.data.startsWith('assistant_text:')) {
                        // Day 23: display LLM assistant text as soon as it's ready
                        const text = ev.data.slice('assistant_text:'.length);
                        try {
                            const container = document.getElementById('chat-history');
                            if (container) {
                                const safe = (text || '').replace(/&/g, '&amp;').replace(/</g, '&lt;');
                                const el = document.createElement('div');
                                el.className = 'message assistant';
                                const avatarText = this.currentPersona ? this.currentPersona.persona.avatar : 'A';
                                el.innerHTML = `<div class="avatar assistant">${avatarText}</div><div class="bubble">${safe}</div>`;
                                container.appendChild(el);
                                container.scrollTop = container.scrollHeight;
                            }
                        } catch (e) { console.warn('Failed to display assistant text', e); }
                    } else if (ev.data.startsWith('audio_chunk:')) {
                        const base64Chunk = ev.data.slice('audio_chunk:'.length);
                        audioChunks.push(base64Chunk);
                        audioChunkCount++;
                        
                        // Day 21: Console acknowledgement of received audio data
                        console.log(`[CLIENT] 🎵 Received audio chunk #${audioChunkCount}`);
                        console.log(`[CLIENT] 📏 Chunk length: ${base64Chunk.length} characters`);
                        console.log(`[CLIENT] 📊 Total chunks accumulated: ${audioChunks.length}`);
                        
                        // Day 22: Play audio chunk immediately for seamless streaming
                        playAudioChunk(base64Chunk);
                        
                        // Update status to show streaming progress
                        statusEl.textContent = `Streaming audio... (${audioChunkCount} chunks received)`;
                    } else if (ev.data.startsWith('audio_complete:')) {
                        const totalChunks = ev.data.slice('audio_complete:'.length);
                        
                        // Day 21: Final audio processing and acknowledgement
                        const combinedAudio = audioChunks.join('');
                        console.log('[CLIENT] 🏁 Audio streaming completed!');
                        console.log(`[CLIENT] ✅ Successfully received ${totalChunks} audio chunks`);
                        console.log(`[CLIENT] 📏 Total combined audio length: ${combinedAudio.length} characters`);
                        console.log(`[CLIENT] 🎵 COMPLETE BASE64 AUDIO DATA:`);
                        console.log(`[CLIENT] ${combinedAudio}`);
                        console.log('[CLIENT] 📸 Audio data streaming acknowledgement complete - ready for LinkedIn screenshot!');
                        
                        // Day 22: Enhanced status with playback info
                        statusEl.textContent = `Audio streaming complete! Playing ${totalChunks} chunks seamlessly...`;
                        // Refresh chat history now that a full turn is completed
                        try { appRef.renderChatHistory(); } catch (_) {}
                        
                        // Reset for next stream
                        setTimeout(() => {
                            if (!isPlaying) {
                                statusEl.textContent = 'Audio playback finished. Ready for next voice input.';
                                // Reset audio context for next session
                                nextStartTime = playbackAudioContext ? playbackAudioContext.currentTime : 0;
                            }
                        }, 1000);
                        // Close WS after completion to allow a clean next round
                        try { if (ws) ws.close(); } catch (_) {}
                    } else if (ev.data.startsWith('audio_error:')) {
                        const error = ev.data.slice('audio_error:'.length);
                        console.error(`[CLIENT] ❌ Audio streaming error: ${error}`);
                        statusEl.textContent = `Audio error: ${error}`;
                        // Ensure chat UI reflects the assistant turn even on audio errors
                        try { appRef.renderChatHistory(); } catch (_) {}
                    }
                };

                if (useTranscription && !forceHttpPipeline && ws) ws.onerror = (err) => {
                    console.error('WebSocket error:', err);
                    statusEl.textContent = 'WebSocket error while streaming.';
                    // Fall back on transport error
                    forceHttpPipeline = true;
                    try { if (processor) processor.disconnect(); } catch (_) {}
                    try { if (sourceNode) sourceNode.disconnect(); } catch (_) {}
                    try { if (captureAudioContext && captureAudioContext.state !== 'closed') captureAudioContext.close(); } catch (_) {}
                    try { if (ws) ws.close(); } catch (_) {}
                    setListeningUI(false);
                    setTimeout(() => { if (!isListening) startRecording(); }, 250);
                };

                if (useTranscription && !forceHttpPipeline && ws) ws.onclose = () => {
                    // Ensure UI resets if socket closes unexpectedly
                    if (mediaRecorder && mediaRecorder.state === 'recording') {
                        try { mediaRecorder.stop(); } catch (_) {}
                    }
                    try { if (processor) processor.disconnect(); } catch (_) {}
                    try { if (sourceNode) sourceNode.disconnect(); } catch (_) {}
                    try { if (captureAudioContext && captureAudioContext.state !== 'closed') captureAudioContext.close(); } catch (_) {}
                    // Signal server we're done but allow time for final transcript
                    try {
                        if (ws && ws.readyState === WebSocket.OPEN) {
                            statusEl.textContent = 'Stopping...';
                            ws.send('done');
                            // Close after short delay to receive final messages
                            setTimeout(() => {
                                try { if (ws && ws.readyState === WebSocket.OPEN) ws.close(); } catch (_) {}
                            }, 1200);
                        }
                    } catch (_) {}
                    setListeningUI(false);
                };
            } catch (err) {
                console.error('Failed to start recording:', err);
                alert('Could not start recording: ' + err.message);
            }
        };

        const stopRecording = () => {
            try { if (mediaRecorder && mediaRecorder.state === 'recording') mediaRecorder.stop(); } catch (_) {}
            try {
                if (streamRef) {
                    streamRef.getTracks().forEach(t => t.stop());
                }
            } catch (_) {}
            try { if (processor) processor.disconnect(); } catch (_) {}
            try { if (sourceNode) sourceNode.disconnect(); } catch (_) {}
            try { if (captureAudioContext && captureAudioContext.state !== 'closed') captureAudioContext.close(); } catch (_) {}
            try { if (ws && ws.readyState === WebSocket.OPEN) ws.send('done'); } catch (_) {}
            try { if (ws) ws.close(); } catch (_) {}
            try { if (fallbackTimerId) clearTimeout(fallbackTimerId); } catch (_) {}
            fallbackTimerId = null;
            setListeningUI(false);
        };

        // Utilities for PCM conversion
        function downsampleBuffer(buffer, sampleRate, outSampleRate) {
            if (outSampleRate === sampleRate) {
                return buffer;
            }
            const sampleRateRatio = sampleRate / outSampleRate;
            const newLength = Math.round(buffer.length / sampleRateRatio);
            const result = new Float32Array(newLength);
            let offsetResult = 0;
            let offsetBuffer = 0;
            while (offsetResult < result.length) {
                const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
                let accum = 0;
                let count = 0;
                for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
                    accum += buffer[i];
                    count++;
                }
                result[offsetResult] = count > 0 ? accum / count : 0;
                offsetResult++;
                offsetBuffer = nextOffsetBuffer;
            }
            return result;
        }

        function floatTo16BitPCM(float32Array) {
            const buffer = new ArrayBuffer(float32Array.length * 2);
            const view = new DataView(buffer);
            let offset = 0;
            for (let i = 0; i < float32Array.length; i++, offset += 2) {
                let s = Math.max(-1, Math.min(1, float32Array[i]));
                view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
            }
            return view;
        }

        toggleBtn.addEventListener('click', async () => {
            if (!isListening) {
                await startRecording();
            } else {
                stopRecording();
            }
        });
    }

    bindNewSession() {
        const btn = document.getElementById('new-session');
        if (!btn) return;
        btn.addEventListener('click', async () => {
            // Create a new session id and reload history view
            this.sessionId = this.generateSessionId();
            try { localStorage.setItem('sessionId', this.sessionId); } catch (_) {}
            const url = new URL(window.location.href);
            url.searchParams.set('session', this.sessionId);
            window.history.replaceState({}, '', url.toString());
            const sessionInfo = document.getElementById('session-info');
            if (sessionInfo) sessionInfo.textContent = `Session: ${this.sessionId}`;
            await this.renderChatHistory();
            
            // Reload current persona for new session (will default to robot)
            await this.loadCurrentPersona();
        });
    }

    async voiceLLMQuery(blob, audioEl, startButton) {
        const uploadStatus = document.getElementById('record-status');
        uploadStatus.textContent = 'Processing: transcribing → LLM → TTS...';

        const formData = new FormData();
        formData.append('file', blob, 'recording.webm');

        try {
            const response = await fetch(`${this.baseUrl}/agent/chat/${encodeURIComponent(this.sessionId)}`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok && data.success && data.audio_url) {
                // Append latest turn to chat history view
                await this.renderChatHistory();
                const transcript = data.transcript ? `Transcript:<br>${data.transcript}<br><br>` : '';
                const llm = data.llm_text ? `Response:<br>${(data.llm_text || '').slice(0, 500)}${data.llm_text.length > 500 ? '…' : ''}<br><br>` : '';
                const note = data.truncated_for_tts ? '(Note: Response truncated to 3000 chars for TTS)' : '';
                uploadStatus.innerHTML = `${transcript}${llm}${note}`;
                audioEl.src = data.audio_url;
                audioEl.style.display = 'none';
                // After playback ends, automatically start recording again
                audioEl.onended = () => {
                    if (startButton) startButton.disabled = false;
                };
                try {
                    await audioEl.play();
                } catch (e) {
                    // Autoplay blocked – show controls and prompt the user
                    console.warn('Autoplay blocked, showing controls', e);
                    audioEl.controls = true;
                    audioEl.style.display = 'block';
                    uploadStatus.textContent = 'Tap Play to hear the response.';
                }
                // Re-enable after playback starts for safety in case onended doesn't fire
                setTimeout(() => { if (startButton) startButton.disabled = false; }, 1000);
            } else {
                    let reason = (data.detail && (data.detail.message || data.detail)) || data.message || 'Unknown error';
                    // Speak fallback if provided
                    const fallback = data.fallback_text || "I'm having trouble connecting right now.";
                    this.speakFallback(fallback);
                throw new Error(reason);
            }
        } catch (error) {
            console.error('Voice LLM query failed:', error);
                this.speakFallback("I'm having trouble connecting right now.");
            uploadStatus.textContent = `Voice LLM failed: ${error.message}`;
        } finally {
            if (startButton) startButton.disabled = false;
        }
    }

    async renderChatHistory() {
        const container = document.getElementById('chat-history');
        if (!container) return;
        try {
            const res = await fetch(`${this.baseUrl}/agent/chat/${encodeURIComponent(this.sessionId)}/history`);
            const data = await res.json();
            const msgs = Array.isArray(data.messages) ? data.messages : [];
            if (msgs.length === 0) {
                container.innerHTML = '<em>No messages yet...</em>';
                return;
            }
            const html = msgs.map(m => {
                const isUser = m.role === 'user';
                const roleClass = isUser ? 'user' : 'assistant';
                const avatarText = isUser ? 'U' : (this.currentPersona ? this.currentPersona.persona.avatar : 'A');
                const safe = (m.text || '').replace(/&/g, '&amp;').replace(/</g, '&lt;');
                return `<div class="message ${roleClass}">
                    <div class="avatar ${roleClass}">${avatarText}</div>
                    <div class="bubble">${safe}</div>
                </div>`;
            }).join('');
            container.innerHTML = html;
            container.scrollTop = container.scrollHeight;
        } catch (e) {
            container.innerHTML = '<em>Failed to load history</em>';
        }
    }

    ensureSessionId() {
        const url = new URL(window.location.href);
        let sessionFromUrl = url.searchParams.get('session');
        let sessionFromStorage = null;
        try { sessionFromStorage = localStorage.getItem('sessionId') || null; } catch (_) {}

        let session = sessionFromUrl || sessionFromStorage;
        if (!session) {
            session = this.generateSessionId();
        }

        // Sync URL and localStorage
        if (!sessionFromUrl || sessionFromUrl !== session) {
            url.searchParams.set('session', session);
            window.history.replaceState({}, '', url.toString());
        }
        try { localStorage.setItem('sessionId', session); } catch (_) {}
        return session;
    }

    generateSessionId() {
        // Simple 12-char base36 id
        return Math.random().toString(36).slice(2, 14);
    }

    async uploadAudio(blob) {
        const uploadStatus = document.getElementById('upload-status');
        uploadStatus.textContent = 'Uploading...';

        const formData = new FormData();
        formData.append('file', blob, 'recording.webm');

        try {
            const response = await fetch(`${this.baseUrl}/api/audio/upload`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok) {
                uploadStatus.innerHTML = `
                    Upload successful!<br>
                    Filename: ${data.filename}<br>
                    Content-Type: ${data.content_type}<br>
                    Size: ${data.size} bytes
                `;
            } else {
                throw new Error(data.detail || 'Upload failed');
            }
        } catch (error) {
            console.error('Upload failed:', error);
            uploadStatus.textContent = `Upload failed: ${error.message}`;
        }
    }

    async transcribeAudio(blob) {
        const uploadStatus = document.getElementById('upload-status');
        uploadStatus.textContent = 'Transcribing...';

        const formData = new FormData();
        formData.append('file', blob, 'recording.webm');

        try {
            const response = await fetch(`${this.baseUrl}/transcribe/file`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok && data.transcript) {
                uploadStatus.innerHTML = `Transcription:<br>${data.transcript}`;
            } else {
                throw new Error(data.detail || 'Transcription failed');
            }
        } catch (error) {
            console.error('Transcription failed:', error);
            uploadStatus.textContent = `Transcription failed: ${error.message}`;
        }
    }

    async echoWithMurf(blob, audioEl) {
        const uploadStatus = document.getElementById('upload-status');
        uploadStatus.textContent = 'Transcribing and generating Murf audio...';

        const formData = new FormData();
        formData.append('file', blob, 'recording.webm');

        try {
            const response = await fetch(`${this.baseUrl}/tts/echo`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (response.ok && data.success && data.audio_url) {
                uploadStatus.innerHTML = `Transcript:<br>${data.transcript || ''}`;
                audioEl.src = data.audio_url;
                audioEl.style.display = 'block';
                await audioEl.play();
            } else {
                let reason = (data.detail && (data.detail.message || data.detail)) || data.message || 'Unknown error';
                const fallback = data.fallback_text || "I'm having trouble connecting right now.";
                this.speakFallback(fallback);
                throw new Error(reason);
            }
        } catch (error) {
            console.error('Echo with Murf failed:', error);
            this.speakFallback("I'm having trouble connecting right now.");
            uploadStatus.textContent = `Echo failed: ${error.message}`;
        }
    }

    speakFallback(text) {
        try {
            const synth = window.speechSynthesis;
            if (!synth) return;
            const utter = new SpeechSynthesisUtterance(text);
            utter.lang = 'en-US';
            synth.cancel();
            synth.speak(utter);
        } catch (_) {
            // no-op
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new App();
});
