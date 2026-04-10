/**
 * NapsterLegal Audio Player
 * ─────────────────────────
 * This file does two things:
 * 1. Defines the Alpine.js component "audioPlayer()" used in player.html
 * 2. Exposes a global playTrack() function called by track cards
 *
 * HOW ALPINE.JS WORKS (quick explanation):
 * - x-data="audioPlayer()" tells Alpine: "use this object as the data for this element"
 * - Every property (playing, volume...) becomes reactive — when it changes, the HTML updates automatically
 * - Every method (togglePlay, seek...) can be called from HTML with @click="methodName()"
 */

function audioPlayer() {
  return {
    // ── STATE (these are the "variables" of the player) ──────────
    currentTrack: null,   // the track currently loaded { title, artist, cover, url }
    playing:      false,  // is audio playing right now?
    currentTime:  0,      // current position in seconds
    duration:     0,      // total duration of the track in seconds
    progress:     0,      // percentage 0-100 for the progress bar
    volume:       80,     // volume level 0-100
    muted:        false,  // is audio muted?
    shuffle:      false,  // shuffle mode on/off
    repeat:       false,  // repeat mode on/off
    queue:        [],     // list of tracks queued up
    queueIndex:   0,      // which track in the queue we're on

    // ── INIT — runs once when Alpine sets up the component ───────
    init() {
      // Register keyboard shortcuts on the document
      document.addEventListener('keydown', (e) => {
        // Don't fire shortcuts while user is typing in an input
        const tag = document.activeElement.tagName.toLowerCase();
        if (['input', 'textarea', 'select'].includes(tag)) return;

        // Don't fire if no track is loaded
        if (!this.currentTrack) return;

        switch (e.code) {
          case 'Space':
            e.preventDefault();
            this.togglePlay();
            break;

          case 'ArrowRight':
            e.preventDefault();
            if (e.shiftKey) {
              // Shift+→ → next track
              this.next();
            } else {
              // → → seek forward 5 seconds
              this.$refs.audio.currentTime = Math.min(
                this.$refs.audio.currentTime + 5,
                this.duration
              );
            }
            break;

          case 'ArrowLeft':
            e.preventDefault();
            if (e.shiftKey) {
              // Shift+← → previous track
              this.previous();
            } else {
              // ← → seek backward 5 seconds
              this.$refs.audio.currentTime = Math.max(
                this.$refs.audio.currentTime - 5,
                0
              );
            }
            break;

          case 'ArrowUp':
            e.preventDefault();
            // ↑ → volume up by 10
            this.volume = Math.min(this.volume + 10, 100);
            this.setVolume();
            break;

          case 'ArrowDown':
            e.preventDefault();
            // ↓ → volume down by 10
            this.volume = Math.max(this.volume - 10, 0);
            this.setVolume();
            break;

          case 'KeyM':
            e.preventDefault();
            this.toggleMute();
            break;

          case 'KeyR':
            e.preventDefault();
            this.toggleRepeat();
            break;

          case 'KeyS':
            e.preventDefault();
            this.toggleShuffle();
            break;
        }
      });
    },

    // ── COMPUTED: format seconds into "m:ss" ─────────────────────
    formatTime(seconds) {
      // Math.floor removes decimals: 90.5 → 90
      const mins = Math.floor(seconds / 60);
      const secs = Math.floor(seconds % 60);
      // padStart(2, '0') adds a leading zero if needed: 5 → "05"
      return `${mins}:${secs.toString().padStart(2, '0')}`;
    },

    // ── LOAD A TRACK ─────────────────────────────────────────────
    loadTrack(track) {
      // $refs.audio is the <audio> element in the template (x-ref="audio")
      this.currentTrack = track;
      this.$refs.audio.src = track.url;
      this.$refs.audio.load();
      this.play();
    },

    // ── PLAY ─────────────────────────────────────────────────────
    play() {
      // .play() returns a Promise — we use .then() to set playing=true only after it starts
      this.$refs.audio.play().then(() => {
        this.playing = true;
      }).catch(err => {
        console.error('Playback failed:', err);
      });
    },

    // ── PAUSE ────────────────────────────────────────────────────
    pause() {
      this.$refs.audio.pause();
      this.playing = false;
    },

    // ── TOGGLE PLAY/PAUSE ────────────────────────────────────────
    togglePlay() {
      if (this.playing) {
        this.pause();
      } else {
        this.play();
      }
    },

    // ── NEXT TRACK ───────────────────────────────────────────────
    next() {
      if (this.queue.length === 0) return;
      if (this.shuffle) {
        // Pick a random index different from current
        let randomIndex;
        do {
          randomIndex = Math.floor(Math.random() * this.queue.length);
        } while (randomIndex === this.queueIndex && this.queue.length > 1);
        this.queueIndex = randomIndex;
      } else {
        // Move to next, loop back to start if at end
        this.queueIndex = (this.queueIndex + 1) % this.queue.length;
      }
      this.loadTrack(this.queue[this.queueIndex]);
    },

    // ── PREVIOUS TRACK ───────────────────────────────────────────
    previous() {
      if (this.currentTime > 3) {
        // If more than 3 seconds in — restart current track
        this.$refs.audio.currentTime = 0;
        return;
      }
      if (this.queue.length === 0) return;
      // Go back one, loop to end if at start
      this.queueIndex = (this.queueIndex - 1 + this.queue.length) % this.queue.length;
      this.loadTrack(this.queue[this.queueIndex]);
    },

    // ── SEEK (click on progress bar) ─────────────────────────────
    seek(event) {
      // event.currentTarget is the progress bar div
      const bar    = event.currentTarget;
      const rect   = bar.getBoundingClientRect();
      // Calculate where on the bar the user clicked (0.0 to 1.0)
      const ratio  = (event.clientX - rect.left) / rect.width;
      // Set audio position to that ratio of total duration
      this.$refs.audio.currentTime = ratio * this.duration;
    },

    // ── VOLUME ───────────────────────────────────────────────────
    setVolume() {
      // HTML audio volume is 0.0 to 1.0, our slider is 0-100
      this.$refs.audio.volume = this.volume / 100;
      // If user drags volume up while muted, unmute automatically
      if (this.volume > 0 && this.muted) {
        this.muted = false;
        this.$refs.audio.muted = false;
      }
    },

    // ── MUTE / UNMUTE ────────────────────────────────────────────
    toggleMute() {
      this.muted = !this.muted;
      this.$refs.audio.muted = this.muted;
    },

    // ── TOGGLE SHUFFLE ───────────────────────────────────────────
    toggleShuffle() {
      this.shuffle = !this.shuffle;
    },

    // ── TOGGLE REPEAT ────────────────────────────────────────────
    toggleRepeat() {
      this.repeat = !this.repeat;
      this.$refs.audio.loop = this.repeat;
    },

    // ── AUDIO EVENTS (called by @timeupdate, @ended, @loadedmetadata) ──

    onTimeUpdate() {
      this.currentTime = this.$refs.audio.currentTime;
      // Calculate progress percentage for the bar
      if (this.duration > 0) {
        this.progress = (this.currentTime / this.duration) * 100;
      }
    },

    onLoaded() {
      // Called when audio metadata is loaded — we now know the duration
      this.duration = this.$refs.audio.duration;
      this.setVolume();
    },

    onEnded() {
      this.playing = false;
      if (this.repeat) {
        // repeat is handled by audio.loop, but just in case
        this.play();
      } else if (this.queue.length > 1) {
        this.next();
      }
    },
  };
}

/**
 * playTrack() — called by clicking any track card
 * ─────────────────────────────────────────────────
 * This is a GLOBAL function (on window) so any HTML element can call it.
 * It dispatches a custom event that Alpine.js picks up to load the track.
 */
function playTrack(id, title, artist, cover, streamUrl) {
  const track = { id, title, artist, cover, url: streamUrl };

  // Alpine.js stores its component data on the DOM element
  // We find the player element and access its Alpine data directly
  const playerEl = document.getElementById('audio-player');
  if (playerEl && playerEl._x_dataStack) {
    const playerData = playerEl._x_dataStack[0];
    // Add to queue if not already in it
    const exists = playerData.queue.find(t => t.id === id);
    if (!exists) {
      playerData.queue.push(track);
      playerData.queueIndex = playerData.queue.length - 1;
    } else {
      playerData.queueIndex = playerData.queue.indexOf(exists);
    }
    playerData.loadTrack(track);
  }
}

// ── MUSIC VISUALIZER ANIMATION ────────────────────────────────────────────
// Creates a floating particle / waveform animation fixed to the page
// that activates when music plays and stops when music pauses.
(function() {
    const CANVAS_ID = 'nl-visualizer';

    function createVisualizer() {
        if (document.getElementById(CANVAS_ID)) return;

        const canvas = document.createElement('canvas');
        canvas.id     = CANVAS_ID;
        canvas.width  = window.innerWidth;
        canvas.height = window.innerHeight;
        canvas.style.cssText = `
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            pointer-events: none;
            z-index: 1;
            opacity: 0;
            transition: opacity 1s ease;
        `;
        document.body.appendChild(canvas);

        window.addEventListener('resize', () => {
            canvas.width  = window.innerWidth;
            canvas.height = window.innerHeight;
        });

        return canvas;
    }

    // Particles
    function makeParticle(canvas) {
        return {
            x:       Math.random() * canvas.width,
            y:       Math.random() * canvas.height,
            r:       Math.random() * 2 + 0.5,
            dx:      (Math.random() - 0.5) * 0.4,
            dy:      -(Math.random() * 0.6 + 0.2),
            alpha:   Math.random() * 0.4 + 0.1,
            color:   ['79,142,247','139,92,246','45,212,191','244,114,182'][
                         Math.floor(Math.random() * 4)],
            reset(c) {
                this.x = Math.random() * c.width;
                this.y = c.height + 10;
                this.alpha = Math.random() * 0.4 + 0.1;
            }
        };
    }

    let particles = [];
    let animFrame = null;
    let active    = false;

    function startAnimation() {
        const canvas = document.getElementById(CANVAS_ID) || createVisualizer();
        if (!canvas) return;
        canvas.style.opacity = '1';
        active = true;

        if (!particles.length) {
            for (let i = 0; i < 60; i++) particles.push(makeParticle(canvas));
        }

        const ctx = canvas.getContext('2d');
        function draw() {
            if (!active) return;
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            particles.forEach(p => {
                p.x += p.dx;
                p.y += p.dy;
                if (p.y < -10) p.reset(canvas);

                ctx.beginPath();
                ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(${p.color},${p.alpha})`;
                ctx.fill();
            });
            animFrame = requestAnimationFrame(draw);
        }
        if (animFrame) cancelAnimationFrame(animFrame);
        draw();
    }

    function stopAnimation() {
        active = false;
        if (animFrame) { cancelAnimationFrame(animFrame); animFrame = null; }
        const canvas = document.getElementById(CANVAS_ID);
        if (canvas) canvas.style.opacity = '0';
    }

    // Watch the Alpine player for play/pause events
    function attachToPlayer() {
        const el = document.getElementById('audio-player');
        if (!el) { setTimeout(attachToPlayer, 500); return; }
        try {
            const p = Alpine.$data(el);
            if (!p || !p.audio) { setTimeout(attachToPlayer, 500); return; }

            // Create visualizer canvas immediately
            createVisualizer();

            p.audio.addEventListener('play',  startAnimation);
            p.audio.addEventListener('pause', stopAnimation);
            p.audio.addEventListener('ended', stopAnimation);

            // If already playing when page restored
            if (!p.audio.paused) startAnimation();

        } catch(e) { setTimeout(attachToPlayer, 500); }
    }

    document.addEventListener('DOMContentLoaded', () => setTimeout(attachToPlayer, 800));
})();
