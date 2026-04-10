"""
acoustid_check.py
─────────────────
Checks an uploaded audio file against the AcoustID database.
AcoustID uses audio fingerprinting (Chromaprint/fpcalc) to identify
whether a track matches a known published song.

HOW IT WORKS:
1. fpcalc analyzes the audio file and produces a unique fingerprint
2. We send the fingerprint to the AcoustID API
3. The API returns matching recordings from the MusicBrainz database
4. If a match is found by a DIFFERENT artist — we flag it as suspicious
5. If no match — the track is likely original

IMPORTANT:
- This only catches songs already in the AcoustID/MusicBrainz database
- New original songs will always pass (no record of them exists yet)
- It is not 100% foolproof — it's a first line of defense
"""

import os
import subprocess
import json

# Free AcoustID API key — register at https://acoustid.org/api-key
# For the school project, use this test key or register for free
ACOUSTID_API_KEY = os.environ.get('ACOUSTID_API_KEY', '7mcE59W7cX')


def get_fingerprint(audio_file_path):
    """
    Run fpcalc on the audio file to get its Chromaprint fingerprint.
    Returns (duration, fingerprint) or raises an exception.

    fpcalc is part of the libchromaprint-tools package.
    Install: sudo apt install -y libchromaprint-tools
    """
    try:
        result = subprocess.run(
            ['fpcalc', '-json', audio_file_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            raise Exception(f"fpcalc error: {result.stderr}")

        data = json.loads(result.stdout)
        return data['duration'], data['fingerprint']

    except FileNotFoundError:
        raise Exception(
            "fpcalc not found. Install with: sudo apt install -y libchromaprint-tools")
    except subprocess.TimeoutExpired:
        raise Exception("fpcalc timed out — audio file may be too large or corrupt")


def query_acoustid(duration, fingerprint):
    """
    Query the AcoustID API with the fingerprint.
    Returns a list of matching recordings.
    Each recording has: id, title, artists list.
    """
    try:
        import acoustid
        results = acoustid.lookup(
            ACOUSTID_API_KEY,
            fingerprint,
            duration,
            meta='recordings'
        )
        matches = []
        for score, recording_id, title, artist in acoustid.parse_lookup_result(results):
            matches.append({
                'score':        round(score, 3),
                'recording_id': recording_id,
                'title':        title or 'Unknown',
                'artist':       artist or 'Unknown',
            })
        return matches

    except Exception as e:
        raise Exception(f"AcoustID API error: {e}")


def check_track(audio_file_path, uploader_stage_name):
    """
    Main function — call this on every track upload.

    Returns a dict:
    {
        'status':  'passed' | 'failed' | 'error' | 'no_match',
        'matches': [...],   # list of matching songs found
        'message': '...',   # human-readable explanation
        'raw':     {...},   # full API response for admin
    }

    'passed'   = no matches found — likely original
    'no_match' = no matches found (same as passed)
    'failed'   = fingerprint matches a known song by a DIFFERENT artist
    'error'    = fpcalc or API failed — allow upload but flag for manual review
    """
    try:
        # Step 1: Generate fingerprint
        duration, fingerprint = get_fingerprint(audio_file_path)

        # Step 2: Query AcoustID
        matches = query_acoustid(duration, fingerprint)

        if not matches:
            # No match in database — probably an original track
            return {
                'status':  'passed',
                'matches': [],
                'message': 'No matching songs found in the AcoustID database. '
                           'Your track appears to be original.',
                'raw':     {'duration': duration, 'matches': []},
            }

        # Step 3: Check if any match is by a DIFFERENT artist
        suspicious = []
        for match in matches:
            # High confidence match (score > 0.7) by someone else
            if match['score'] > 0.7:
                artist_lower   = match['artist'].lower().strip()
                uploader_lower = uploader_stage_name.lower().strip()
                # If the matched artist name is clearly different from uploader
                if artist_lower and uploader_lower not in artist_lower \
                        and artist_lower not in uploader_lower:
                    suspicious.append(match)

        if suspicious:
            return {
                'status':  'failed',
                'matches': suspicious,
                'message': f"This audio matches '{suspicious[0]['title']}' "
                           f"by '{suspicious[0]['artist']}' in our database "
                           f"(confidence: {suspicious[0]['score']*100:.0f}%). "
                           f"Upload rejected to protect copyright.",
                'raw':     {'duration': duration, 'matches': matches},
            }

        # Matches found but could be the same artist or low confidence
        return {
            'status':  'passed',
            'matches': matches,
            'message': 'Fingerprint check passed. Low-confidence or same-artist matches found.',
            'raw':     {'duration': duration, 'matches': matches},
        }

    except Exception as e:
        # Never block an upload due to a technical error
        # Flag for manual admin review instead
        return {
            'status':  'error',
            'matches': [],
            'message': f'Fingerprint check could not complete: {str(e)}. '
                       f'Track flagged for manual admin review.',
            'raw':     {'error': str(e)},
        }
