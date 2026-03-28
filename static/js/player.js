/**
 * NapsterLegal Audio Player
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
    //  STATE (these are the "variables" of the player) 
    currentTrack: null,   // the track currently loaded { title, artist, cover, url }
    playing:      false,  // is audio playing right now?
    currentTime:  0,      // current position in seconds
    duration:     0,      // total duration of the track in seconds
    progress:     0,      // percentage 0-100 for the progress bar
    volume:       80,     // volume level 0-100
    shuffle:      false,  // shuffle mode on/off
    repeat:       false,  // repeat mode on/off
    queue:        [],     // list of tracks queued up
    queueIndex:   0,      // which track in the queue we're on

    //COMPUTED: format seconds into "m:ss" 
    formatTime(seconds) {
      // Math.floor removes decimals: 90.5 → 90
      const mins = Math.floor(seconds / 60);
      const secs = Math.floor(seconds % 60);
      // padStart(2, '0') adds a leading zero if needed: 5 → "05"
      return `${mins}:${secs.toString().padStart(2, '0')}`;
    },

    //LOAD A TRACK 
    loadTrack(track) {
      // $refs.audio is the <audio> element in the template (x-ref="audio")
      this.currentTrack = track;
      this.$refs.audio.src = track.url;
      this.$refs.audio.load();
      this.play();
    },

    // PLAY 
    play() {
      // .play() returns a Promise — we use .then() to set playing=true only after it starts
      this.$refs.audio.play().then(() => {
        this.playing = true;
      }).catch(err => {
        console.error('Playback failed:', err);
      });
    },

    // PAUSE 
    pause() {
      this.$refs.audio.pause();
      this.playing = false;
    },

    //  TOGGLE PLAY/PAUSE 
    togglePlay() {
      if (this.playing) {
        this.pause();
      } else {
        this.play();
      }
    },

    // NEXT TRACK 
    next() {
      // Report partial listen before skipping
      if (this.currentTrack && this.currentTime > 5) {
        reportListenDuration(this.currentTrack.id, this.currentTime, false);
      }
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

    // PREVIOUS TRACK 
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

    //  SEEK (click on progress bar) 
    seek(event) {
      // event.currentTarget is the progress bar div
      const bar    = event.currentTarget;
      const rect   = bar.getBoundingClientRect();
      // Calculate where on the bar the user clicked (0.0 to 1.0)
      const ratio  = (event.clientX - rect.left) / rect.width;
      // Set audio position to that ratio of total duration
      this.$refs.audio.currentTime = ratio * this.duration;
    },

    // VOLUME
    setVolume() {
      // HTML audio volume is 0.0 to 1.0, our slider is 0-100
      this.$refs.audio.volume = this.volume / 100;
    },

    // TOGGLE SHUFFLE 
    toggleShuffle() {
      this.shuffle = !this.shuffle;
    },

    //  TOGGLE REPEAT 
    toggleRepeat() {
      this.repeat = !this.repeat;
      this.$refs.audio.loop = this.repeat;
    },

    //  AUDIO EVENTS (called by @timeupdate, @ended, @loadedmetadata)

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
      // Report full listen to server
      if (this.currentTrack) {
        reportListenDuration(this.currentTrack.id, this.duration, true);
      }
      if (this.repeat) {
        this.play();
      } else if (this.queue.length > 1) {
        this.next();
      }
    },
  };
}

/**
 * playTrack() — called by clicking any track card
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


/**
 * reportListenDuration()
 * Called when a track ends or the user skips away.
 * Sends the actual listened duration back to the server
 * so MariaDB PlayEvent gets updated with real data.
 */
function reportListenDuration(trackId, duration, completed) {
  const csrfToken = document.cookie
    .split(';')
    .find(c => c.trim().startsWith('csrftoken='))
    ?.split('=')[1];

  if (!trackId || !csrfToken) return;

  // Use sendBeacon so it works even when the page is closing
  const data = new FormData();
  data.append('track_id', trackId);
  data.append('duration', Math.floor(duration));
  data.append('completed', completed ? '1' : '0');
  data.append('csrfmiddlewaretoken', csrfToken);

  navigator.sendBeacon('/api/log-listen/', data);
}
