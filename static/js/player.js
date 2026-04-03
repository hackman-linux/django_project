/**
 * NapsterLegal Audio Player
 * Vanilla JS + Alpine.js
 * Features: play/pause, queue, shuffle, repeat,
 *           seek, volume, spacebar control, listen tracking
 */

// ── Spacebar global listener (works on any page) ──────────────
document.addEventListener('keydown', function(e) {
    // Only trigger if not typing in an input/textarea
    const tag = document.activeElement.tagName.toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select') return;

    if (e.code === 'Space') {
        e.preventDefault();
        const playerEl = document.getElementById('audio-player');
        if (playerEl) {
            const player = Alpine.$data(playerEl);
            if (player && player.currentTrack) {
                player.toggle();
            }
        }
    }
    // Arrow right = next track
    if (e.code === 'ArrowRight' && e.altKey) {
        e.preventDefault();
        const player = Alpine.$data(document.getElementById('audio-player'));
        if (player) player.next();
    }
    // Arrow left = previous track
    if (e.code === 'ArrowLeft' && e.altKey) {
        e.preventDefault();
        const player = Alpine.$data(document.getElementById('audio-player'));
        if (player) player.prev();
    }
});

function audioPlayer() {
    return {
        audio:        null,
        playing:      false,
        currentTrack: null,
        queue:        [],
        currentIndex: 0,
        currentTime:  0,
        duration:     0,
        volume:       0.8,
        shuffle:      false,
        repeat:       false,
        visible:      false,

        init() {
            this.audio = new Audio();
            this.audio.volume = this.volume;

            this.audio.addEventListener('timeupdate', () => {
                this.currentTime = this.audio.currentTime;
                this.duration    = this.audio.duration || 0;
            });

            this.audio.addEventListener('ended', () => {
                this.onEnded();
            });

            this.audio.addEventListener('loadedmetadata', () => {
                this.duration = this.audio.duration;
            });

            // Report listen on page close
            window.addEventListener('beforeunload', () => {
                if (this.currentTrack && this.currentTime > 3) {
                    this._reportDuration(false);
                }
            });
        },

        loadTrack(track) {
            if (this.currentTrack && this.currentTime > 3) {
                this._reportDuration(false);
            }
            this.currentTrack = track;
            this.audio.src    = track.streamUrl;
            this.audio.load();
            this.currentTime  = 0;
            this.duration     = 0;
        },

        play() {
            if (!this.currentTrack) return;
            this.audio.play()
                .then(() => { this.playing = true; })
                .catch(e => console.warn('Play blocked:', e));
        },

        pause() {
            this.audio.pause();
            this.playing = false;
        },

        toggle() {
            this.playing ? this.pause() : this.play();
        },

        playNow(track) {
            const idx = this.queue.findIndex(t => t.id === track.id);
            if (idx === -1) {
                this.queue.unshift(track);
                this.currentIndex = 0;
            } else {
                this.currentIndex = idx;
            }
            this.loadTrack(track);
            this.visible = true;
            this.play();
        },

        next() {
            if (this.currentTrack && this.currentTime > 3) {
                this._reportDuration(false);
            }
            if (this.queue.length === 0) return;

            if (this.shuffle) {
                let idx;
                do {
                    idx = Math.floor(Math.random() * this.queue.length);
                } while (idx === this.currentIndex && this.queue.length > 1);
                this.currentIndex = idx;
            } else {
                this.currentIndex = (this.currentIndex + 1) % this.queue.length;
            }
            this.loadTrack(this.queue[this.currentIndex]);
            this.play();
        },

        prev() {
            // If > 3 seconds in: restart current track
            if (this.currentTime > 3) {
                this.audio.currentTime = 0;
                if (!this.playing) this.play();
                return;
            }
            if (this.currentTrack && this.currentTime > 0) {
                this._reportDuration(false);
            }
            this.currentIndex =
                (this.currentIndex - 1 + this.queue.length) % this.queue.length;
            this.loadTrack(this.queue[this.currentIndex]);
            this.play();
        },

        onEnded() {
            this.playing = false;
            if (this.currentTrack) {
                this._reportDuration(true);
            }
            if (this.repeat) {
                this.audio.currentTime = 0;
                this.play();
            } else if (this.queue.length > 1) {
                this.next();
            }
        },

        seek(event) {
            const rect  = event.currentTarget.getBoundingClientRect();
            const ratio = (event.clientX - rect.left) / rect.width;
            this.audio.currentTime = Math.max(0,
                Math.min(ratio * this.duration, this.duration));
        },

        setVolume(event) {
            const rect    = event.currentTarget.getBoundingClientRect();
            const ratio   = (event.clientX - rect.left) / rect.width;
            this.volume   = Math.max(0, Math.min(ratio, 1));
            this.audio.volume = this.volume;
        },

        formatTime(secs) {
            if (!secs || isNaN(secs)) return '0:00';
            const m = Math.floor(secs / 60);
            const s = Math.floor(secs % 60);
            return `${m}:${s.toString().padStart(2, '0')}`;
        },

        get progressPercent() {
            return this.duration ? (this.currentTime / this.duration) * 100 : 0;
        },

        _reportDuration(completed) {
            if (!this.currentTrack) return;
            const listened = Math.floor(this.currentTime);
            if (listened < 2) return;

            const csrf = document.cookie
                .split(';')
                .find(c => c.trim().startsWith('csrftoken='))
                ?.split('=')[1];
            if (!csrf) return;

            const data = new FormData();
            data.append('track_id',           this.currentTrack.id);
            data.append('duration',            listened);
            data.append('completed',           completed ? '1' : '0');
            data.append('csrfmiddlewaretoken', csrf);

            navigator.sendBeacon('/api/log-listen/', data);
        },
    };
}

function playTrack(id, title, artist, cover, streamUrl) {
    const player = Alpine.$data(document.getElementById('audio-player'));
    if (!player) { console.error('Player not found'); return; }
    player.playNow({ id, title, artist, cover, streamUrl });
}

function addToQueue(id, title, artist, cover, streamUrl) {
    const player = Alpine.$data(document.getElementById('audio-player'));
    if (!player) return;
    player.queue.push({ id, title, artist, cover, streamUrl });
}
