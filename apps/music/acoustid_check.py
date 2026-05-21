"""
NapsterLegal — AcoustID Fingerprint Check
Checks if an audio file matches known recordings.
Returns a result dict that the upload view interprets.

Requires: fpcalc (chromaprint), pyacoustid
Install:  sudo apt install libchromaprint-tools
          pip install pyacoustid --break-system-packages
"""
import os


def check_acoustid(file_path):
    """
    Run AcoustID fingerprint check on an audio file.

    Returns:
        {
          'status': 'passed' | 'duplicate' | 'error' | 'no_match',
          'score':  float 0.0–1.0,
          'artist': str,
          'recording_id': str,
          'error': str (only on error),
        }
    """
    try:
        import acoustid

        api_key = os.environ.get('ACOUSTID_API_KEY', '')
        if not api_key:
            # No API key configured — skip fingerprint check
            return {'status': 'error', 'error': 'ACOUSTID_API_KEY not set'}

        results = list(acoustid.match(api_key, file_path))

        if not results:
            return {'status': 'no_match', 'score': 0.0, 'artist': '', 'recording_id': ''}

        # Best match
        score, recording_id, title, artist = results[0]

        return {
            'status':       'matched',
            'score':        score,
            'artist':       artist or '',
            'title':        title  or '',
            'recording_id': recording_id or '',
        }

    except FileNotFoundError:
        return {'status': 'error', 'error': 'fpcalc not found — install chromaprint'}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}
