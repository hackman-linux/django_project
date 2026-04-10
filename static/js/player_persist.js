/**
 * NapsterLegal — Player State Persistence
 * Saves and restores player state across page navigations using sessionStorage.
 * Music "continues" by restoring the track and seeking to the last position.
 */

const STORAGE_KEY = 'nl_player_state';

// Save state before leaving the page
window.addEventListener('beforeunload', function() {
    const el = document.getElementById('audio-player');
    if (!el) return;
    try {
        const p = Alpine.$data(el);
        if (!p || !p.currentTrack) return;
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
            track:        p.currentTrack,
            queue:        p.queue,
            currentIndex: p.currentIndex,
            currentTime:  p.currentTime,
            volume:       p.volume,
            shuffle:      p.shuffle,
            repeat:       p.repeat,
            muted:        p.muted,
            wasPlaying:   p.playing,
        }));
    } catch(e) { /* sessionStorage may be unavailable */ }
});

// Restore state after page loads
document.addEventListener('DOMContentLoaded', function() {
    // Don't restore on settings page
    if (window.location.pathname.includes('/settings') ||
        window.location.pathname.includes('/control/')) return;

    try {
        const raw = sessionStorage.getItem(STORAGE_KEY);
        if (!raw) return;
        const state = JSON.parse(raw);
        if (!state || !state.track) return;

        // Wait for Alpine to initialise the player
        const tryRestore = (attempts) => {
            const el = document.getElementById('audio-player');
            if (!el) return;
            try {
                const p = Alpine.$data(el);
                if (!p || !p.audio) {
                    if (attempts > 0) setTimeout(() => tryRestore(attempts - 1), 200);
                    return;
                }

                p.queue        = state.queue        || [state.track];
                p.currentIndex = state.currentIndex || 0;
                p.shuffle      = state.shuffle      || false;
                p.repeat       = state.repeat       || false;
                p.muted        = state.muted        || false;
                p.volume       = state.volume       || 0.8;
                p.visible      = true;

                // Load track at saved position
                p.loadTrack(state.track);

                // Seek to saved position once audio is ready
                const seekAndPlay = () => {
                    if (state.currentTime > 0) {
                        p.audio.currentTime = state.currentTime;
                        p.currentTime       = state.currentTime;
                    }
                    // Auto-resume if was playing
                    if (state.wasPlaying) {
                        p.play();
                    }
                };

                p.audio.addEventListener('loadedmetadata', seekAndPlay, { once: true });
                p.audio.addEventListener('canplay',        seekAndPlay, { once: true });

            } catch(e) {
                if (attempts > 0) setTimeout(() => tryRestore(attempts - 1), 200);
            }
        };
        setTimeout(() => tryRestore(15), 300);

    } catch(e) { /* ignore */ }
});
