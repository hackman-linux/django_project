/**
 * NapsterLegal — Synchronized Lyrics Display
 *
 * Shows lyrics in a panel below the player when music plays.
 * If no lyrics: shows a rotating vinyl disk animation.
 * Attempts to sync lyrics lines to playback time using line timing estimation.
 */

window.LyricsPlayer = (function() {
  let panel        = null;   // the lyrics panel DOM element
  let lines        = [];     // array of {text, time} objects
  let currentLine  = -1;
  let animFrame    = null;
  let isOpen       = false;
  let currentTrack = null;

  function init() {
    // Create the lyrics panel (positioned above the player bar)
    panel = document.createElement('div');
    panel.id = 'nl-lyrics-panel';
    panel.style.cssText = `
      position: fixed;
      bottom: 80px;
      left: 50%;
      transform: translateX(-50%);
      width: min(540px, 95vw);
      max-height: 280px;
      background: rgba(8,12,20,0.97);
      backdrop-filter: blur(24px);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 20px;
      z-index: 99;
      overflow: hidden;
      transition: all 0.4s cubic-bezier(0.34,1.2,0.64,1);
      opacity: 0;
      pointer-events: none;
      display: flex;
      flex-direction: column;
    `;
    document.body.appendChild(panel);
    return panel;
  }

  function show(track) {
    if (!panel) init();
    currentTrack = track;
    isOpen       = true;
    panel.style.opacity     = '1';
    panel.style.pointerEvents = 'auto';
    panel.style.bottom      = '88px';

    if (track.lyrics && track.lyrics.trim()) {
      _renderLyrics(track.lyrics, track.duration || 0);
    } else {
      _renderAnimation(track);
    }
  }

  function hide() {
    if (!panel) return;
    isOpen             = false;
    panel.style.opacity = '0';
    panel.style.pointerEvents = 'none';
    if (animFrame) { cancelAnimationFrame(animFrame); animFrame = null; }
  }

  function toggle(track) {
    if (isOpen && currentTrack && currentTrack.id === track.id) {
      hide();
    } else {
      show(track);
    }
  }

  function update(currentTime) {
    if (!isOpen || !lines.length) return;
    const idx = _findCurrentLine(currentTime);
    if (idx !== currentLine) {
      currentLine = idx;
      _highlightLine(idx);
    }
  }

  // ── LYRICS RENDERING ─────────────────────────────────────────────────────

  function _renderLyrics(lyricsText, totalDuration) {
    const rawLines = lyricsText.split('\n').filter(l => l.trim());

    // Estimate timing: evenly distribute lines across the song
    const timePerLine = totalDuration > 0
      ? totalDuration / (rawLines.length + 2)
      : 3; // fallback: 3 seconds per line

    lines = rawLines.map((text, i) => ({
      text: text.trim(),
      time: i * timePerLine,
    }));

    panel.innerHTML = `
      <div style="
        display:flex;align-items:center;justify-content:space-between;
        padding:.75rem 1.125rem;border-bottom:1px solid rgba(255,255,255,.06);
        flex-shrink:0;">
        <div style="display:flex;align-items:center;gap:.5rem;">
          <svg width="14" height="14" fill="none" stroke="#4F8EF7" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
          <span style="font-size:.8125rem;font-weight:600;color:#F0F4FF;">Lyrics</span>
          <span id="nl-lyrics-track-name"
                style="font-size:.6875rem;color:#4A5568;max-width:200px;
                       overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"></span>
        </div>
        <button onclick="LyricsPlayer.hide()"
                style="background:none;border:none;cursor:pointer;color:#4A5568;padding:4px;
                       border-radius:6px;transition:color .15s;"
                onmouseover="this.style.color='#F0F4FF'"
                onmouseout="this.style.color='#4A5568'">
          <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>
      <div id="nl-lyrics-scroll"
           style="overflow-y:auto;padding:1rem 1.125rem;flex:1;
                  scrollbar-width:thin;scrollbar-color:rgba(79,142,247,.2) transparent;">
        ${lines.map((l, i) => `
          <p id="nl-line-${i}"
             style="font-size:.9375rem;line-height:1.8;text-align:center;
                    color:#4A5568;transition:all .35s;margin:0;padding:.25rem 0;
                    cursor:pointer;"
             onclick="LyricsPlayer._seekToLine(${i})"
             data-time="${l.time}">
            ${l.text || '&nbsp;'}
          </p>
        `).join('')}
      </div>
    `;
    currentLine = -1;
  }

  // ── ANIMATION (no lyrics) ─────────────────────────────────────────────────

  function _renderAnimation(track) {
    lines = []; // no sync needed
    panel.innerHTML = `
      <div style="
        display:flex;align-items:center;justify-content:space-between;
        padding:.75rem 1.125rem;border-bottom:1px solid rgba(255,255,255,.06);
        flex-shrink:0;">
        <span style="font-size:.8125rem;font-weight:600;color:#F0F4FF;">Now Playing</span>
        <button onclick="LyricsPlayer.hide()"
                style="background:none;border:none;cursor:pointer;color:#4A5568;padding:4px;
                       border-radius:6px;transition:color .15s;"
                onmouseover="this.style.color='#F0F4FF'"
                onmouseout="this.style.color='#4A5568'">
          <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>
      <div style="
        flex:1;display:flex;flex-direction:column;align-items:center;
        justify-content:center;padding:1.5rem;gap:1rem;">

        <!-- Spinning vinyl disk -->
        <div id="nl-vinyl" style="
          width: 100px; height: 100px;
          border-radius: 50%;
          position: relative;
          animation: nl-vinyl-spin 2s linear infinite;
          flex-shrink: 0;">

          <!-- Vinyl grooves -->
          <div style="
            position:absolute;inset:0;border-radius:50%;
            background: conic-gradient(
              from 0deg,
              #1a1a2e 0deg, #16213e 30deg, #0f3460 60deg,
              #1a1a2e 90deg, #16213e 120deg, #0f3460 150deg,
              #1a1a2e 180deg, #16213e 210deg, #0f3460 240deg,
              #1a1a2e 270deg, #16213e 300deg, #0f3460 330deg,
              #1a1a2e 360deg
            );
            box-shadow: 0 0 0 2px #4F8EF7, 0 0 20px rgba(79,142,247,.3),
                        inset 0 0 20px rgba(0,0,0,.5);
          "></div>

          <!-- Groove rings -->
          <div style="position:absolute;inset:8px;border-radius:50%;
                      border:1px solid rgba(255,255,255,.06);"></div>
          <div style="position:absolute;inset:18px;border-radius:50%;
                      border:1px solid rgba(255,255,255,.04);"></div>
          <div style="position:absolute;inset:28px;border-radius:50%;
                      border:1px solid rgba(255,255,255,.03);"></div>

          <!-- Cover art in center OR gradient -->
          <div style="
            position:absolute;
            top:50%;left:50%;
            transform:translate(-50%,-50%);
            width:38px;height:38px;
            border-radius:50%;
            overflow:hidden;
            border:2px solid rgba(255,255,255,.15);
            box-shadow:0 0 0 1px rgba(0,0,0,.5);
          ">
            ${track && track.cover
              ? `<img src="${track.cover}" style="width:100%;height:100%;object-fit:cover;"/>`
              : `<div style="width:100%;height:100%;background:linear-gradient(135deg,#4F8EF7,#8B5CF6);
                             display:flex;align-items:center;justify-content:center;">
                   <svg width="14" height="14" fill="white" viewBox="0 0 24 24">
                     <path d="M9 18V5l12-2v13M9 18c0 1.1-1.34 2-3 2s-3-.9-3-2z"/>
                   </svg>
                 </div>`
            }
          </div>

          <!-- Center dot -->
          <div style="
            position:absolute;top:50%;left:50%;
            transform:translate(-50%,-50%);
            width:8px;height:8px;
            border-radius:50%;
            background:#F0F4FF;
            z-index:2;
          "></div>
        </div>

        <!-- Track info -->
        <div style="text-align:center;">
          <p style="font-size:.9375rem;font-weight:700;color:#F0F4FF;margin-bottom:.25rem;">
            ${track ? track.title : 'Playing'}</p>
          <p style="font-size:.8125rem;color:#94A3B8;margin-bottom:.625rem;">
            ${track ? track.artist : ''}</p>
          <p style="font-size:.75rem;color:#4A5568;">No lyrics available for this track</p>
        </div>

        <!-- Sound wave bars -->
        <div style="display:flex;align-items:flex-end;gap:3px;height:20px;">
          ${[1,2,3,4,5,6,7,8].map((_, i) => `
            <div style="
              width:3px;background:#4F8EF7;border-radius:2px;
              animation:nl-wave ${0.6 + i*0.08}s ease-in-out infinite alternate;
              height:${6 + Math.random()*14}px;
            "></div>
          `).join('')}
        </div>
      </div>
    `;

    // Inject CSS animations if not already there
    if (!document.getElementById('nl-anim-style')) {
      const style = document.createElement('style');
      style.id    = 'nl-anim-style';
      style.textContent = `
        @keyframes nl-vinyl-spin {
          from { transform: rotate(0deg); }
          to   { transform: rotate(360deg); }
        }
        @keyframes nl-wave {
          from { transform: scaleY(0.4); }
          to   { transform: scaleY(1); }
        }
        @keyframes spin { to { transform: rotate(360deg); } }
      `;
      document.head.appendChild(style);
    }
  }

  // ── HELPERS ───────────────────────────────────────────────────────────────

  function _findCurrentLine(time) {
    for (let i = lines.length - 1; i >= 0; i--) {
      if (time >= lines[i].time) return i;
    }
    return -1;
  }

  function _highlightLine(idx) {
    const scroll = document.getElementById('nl-lyrics-scroll');
    if (!scroll) return;

    document.querySelectorAll('[id^="nl-line-"]').forEach(el => {
      el.style.color     = '#4A5568';
      el.style.fontSize  = '.9375rem';
      el.style.fontWeight= '400';
      el.style.textShadow= 'none';
    });

    if (idx >= 0) {
      const active = document.getElementById(`nl-line-${idx}`);
      if (active) {
        active.style.color      = '#F0F4FF';
        active.style.fontSize   = '1rem';
        active.style.fontWeight = '700';
        active.style.textShadow = '0 0 20px rgba(79,142,247,.6)';

        // Smooth scroll to active line
        const scrollTop = active.offsetTop - scroll.clientHeight / 2 + active.clientHeight / 2;
        scroll.scrollTo({ top: scrollTop, behavior: 'smooth' });
      }
    }
  }

  function _seekToLine(idx) {
    if (idx < 0 || idx >= lines.length) return;
    const playerEl = document.getElementById('audio-player');
    if (!playerEl) return;
    try {
      const p = Alpine.$data(playerEl);
      if (p && p.audio) {
        p.audio.currentTime = lines[idx].time;
        p.currentTime       = lines[idx].time;
      }
    } catch(e) {}
  }

  // ── PAUSE / RESUME ANIMATION ──────────────────────────────────────────────

  function pauseAnimation() {
    const vinyl = document.getElementById('nl-vinyl');
    if (vinyl) vinyl.style.animationPlayState = 'paused';
    document.querySelectorAll('[style*="nl-wave"]').forEach(el => {
      el.style.animationPlayState = 'paused';
    });
  }

  function resumeAnimation() {
    const vinyl = document.getElementById('nl-vinyl');
    if (vinyl) vinyl.style.animationPlayState = 'running';
    document.querySelectorAll('[style*="nl-wave"]').forEach(el => {
      el.style.animationPlayState = 'running';
    });
  }

  return { init, show, hide, toggle, update, pauseAnimation, resumeAnimation, _seekToLine };
})();
