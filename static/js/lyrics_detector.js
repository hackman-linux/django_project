/**
 * NapsterLegal — Lyrics Auto-Detection
 *
 * Strategy (in order):
 * 1. Search lyrics.ovh FREE API by title + artist name (no key needed)
 * 2. If not found, use Web Speech API to transcribe the audio in real-time
 * 3. If both fail, show a clear message
 */

window.LyricsDetector = {
  
  /**
   * Main entry point — called when artist clicks "Auto-Detect Lyrics"
   * @param {string} title - Track title from the title input
   * @param {string} artist - Artist stage name
   * @param {HTMLElement} audioInput - The file input element
   * @param {HTMLElement} textarea - The lyrics textarea
   * @param {HTMLElement} statusEl - Status message element
   * @param {Function} onLangDetected - Callback when language is detected
   */
  detect: async function(title, artist, audioInput, textarea, statusEl, onLangDetected) {
    if (!title || !title.trim()) {
      this._showStatus(statusEl, 'error', 'Please enter the track title first.');
      return;
    }

    this._showStatus(statusEl, 'loading', `Searching lyrics for "${title}" by ${artist}...`);

    // Step 1: Search lyrics.ovh by title + artist
    const lyricsOvh = await this._fetchLyricsOvh(title, artist);
    if (lyricsOvh) {
      textarea.value = lyricsOvh;
      textarea.dispatchEvent(new Event('input')); // trigger language detection badge
      this._showStatus(statusEl, 'success', '✅ Lyrics found and loaded! Review before saving.');
      if (onLangDetected) onLangDetected(lyricsOvh);
      return;
    }

    // Step 2: Try with just the title (artist name might differ)
    this._showStatus(statusEl, 'loading', 'Trying alternative search...');
    const lyricsTitle = await this._fetchLyricsOvh(title, '');
    if (lyricsTitle) {
      textarea.value = lyricsTitle;
      textarea.dispatchEvent(new Event('input'));
      this._showStatus(statusEl, 'success', '✅ Lyrics found (verify artist match). Review before saving.');
      if (onLangDetected) onLangDetected(lyricsTitle);
      return;
    }

    // Step 3: Try Web Speech API on the audio file
    const files = audioInput ? audioInput.files : null;
    if (files && files[0] && this._speechSupported()) {
      this._showStatus(statusEl, 'loading',
        '🎤 No lyrics database match. Transcribing audio via speech recognition...');
      const transcription = await this._transcribeWithSpeech(files[0], statusEl);
      if (transcription) {
        textarea.value = transcription;
        textarea.dispatchEvent(new Event('input'));
        this._showStatus(statusEl, 'success',
          '✅ Transcription complete! This is a speech-to-text transcript — review carefully.');
        if (onLangDetected) onLangDetected(transcription);
        return;
      }
    }

    // Nothing worked
    this._showStatus(statusEl, 'warning',
      'Could not detect lyrics automatically. This song may not be in our database. '
      + 'Please enter lyrics manually.');
  },

  _fetchLyricsOvh: async function(title, artist) {
    try {
      const a = encodeURIComponent(artist || 'unknown');
      const t = encodeURIComponent(title);
      const url = artist
        ? `https://api.lyrics.ovh/v1/${a}/${t}`
        : `https://api.lyrics.ovh/suggest/${t}`;

      const res = await fetch(url, { signal: AbortSignal.timeout(5000) });
      if (!res.ok) return null;
      const data = await res.json();

      if (data.lyrics && data.lyrics.trim().length > 20) {
        return data.lyrics.trim();
      }
      // Handle suggest endpoint
      if (data.data && data.data.length > 0) {
        const first = data.data[0];
        const res2  = await fetch(
          `https://api.lyrics.ovh/v1/${encodeURIComponent(first.artist.name)}/${encodeURIComponent(first.title)}`,
          { signal: AbortSignal.timeout(5000) });
        if (res2.ok) {
          const d2 = await res2.json();
          if (d2.lyrics && d2.lyrics.trim().length > 20) return d2.lyrics.trim();
        }
      }
      return null;
    } catch {
      return null;
    }
  },

  _speechSupported: function() {
    return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
  },

  _transcribeWithSpeech: function(audioFile, statusEl) {
    return new Promise(resolve => {
      const SR   = window.SpeechRecognition || window.webkitSpeechRecognition;
      const rec  = new SR();
      rec.lang         = 'fr-FR'; // primary language for Francophone Africa
      rec.continuous   = true;
      rec.interimResults = false;
      rec.maxAlternatives = 1;

      const audio  = new Audio();
      const url    = URL.createObjectURL(audioFile);
      audio.src    = url;

      let transcript = '';
      let timeout;

      rec.onresult = e => {
        for (let i = e.resultIndex; i < e.results.length; i++) {
          if (e.results[i].isFinal) {
            transcript += e.results[i][0].transcript + '\n';
          }
        }
        this._showStatus(statusEl, 'loading',
          `🎤 Transcribing... ${transcript.split('\n').length} lines captured`);
      };

      rec.onerror = () => {
        clearTimeout(timeout);
        audio.pause();
        URL.revokeObjectURL(url);
        rec.stop();
        resolve(transcript.trim() || null);
      };

      rec.onend = () => {
        clearTimeout(timeout);
        audio.pause();
        URL.revokeObjectURL(url);
        resolve(transcript.trim() || null);
      };

      // Start audio + recognition together
      audio.play().then(() => {
        rec.start();
        // Stop after 3 minutes max
        timeout = setTimeout(() => {
          rec.stop();
        }, 180000);
      }).catch(() => {
        resolve(null);
      });

      audio.onended = () => rec.stop();
    });
  },

  _showStatus: function(el, type, msg) {
    if (!el) return;
    const styles = {
      success: 'background:rgba(52,211,153,.1);color:#6EE7B7;border:1px solid rgba(52,211,153,.2);',
      error:   'background:rgba(239,68,68,.1);color:#FCA5A5;border:1px solid rgba(239,68,68,.2);',
      warning: 'background:rgba(245,158,11,.1);color:#FDE68A;border:1px solid rgba(245,158,11,.2);',
      loading: 'background:rgba(79,142,247,.1);color:#93C5FD;border:1px solid rgba(79,142,247,.2);',
    };
    el.style.cssText = (styles[type] || styles.loading) +
      'display:block;padding:.5rem .75rem;border-radius:8px;font-size:.8125rem;margin-bottom:.75rem;';
    el.innerHTML = type === 'loading'
      ? `<span style="display:inline-block;animation:spin 1s linear infinite;margin-right:6px;">⟳</span>${msg}`
      : msg;
  }
};
