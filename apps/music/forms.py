"""
NapsterLegal — Music Forms
Clean ModelForm for track upload — no magic, no missing fields.
"""
from django import forms
from .models import Track, Genre


class TrackUploadForm(forms.ModelForm):
    """
    Track upload form.
    All validation happens here so views stay clean.
    """
    class Meta:
        model  = Track
        fields = [
            'title', 'audio_file', 'cover_image',
            'genre', 'license_type', 'lyrics',
            'is_explicit', 'bpm',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Enter your track title',
                'required': True,
            }),
            'lyrics': forms.Textarea(attrs={
                'placeholder': 'Paste your lyrics here (optional)...',
                'rows': 8,
            }),
            'bpm': forms.NumberInput(attrs={
                'placeholder': 'e.g. 120',
                'min': 40, 'max': 300,
            }),
        }

    def clean_audio_file(self):
        f = self.cleaned_data.get('audio_file')
        if not f:
            raise forms.ValidationError('Audio file is required.')

        import os
        ext = os.path.splitext(f.name)[1].lower()
        allowed = ['.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac']
        if ext not in allowed:
            raise forms.ValidationError(
                f'File type "{ext}" not allowed. Accepted: {", ".join(allowed)}')

        max_mb = 200
        if f.size > max_mb * 1024 * 1024:
            raise forms.ValidationError(
                f'File too large. Maximum is {max_mb}MB.')

        return f

    def clean_title(self):
        t = self.cleaned_data.get('title', '').strip()
        if not t:
            raise forms.ValidationError('Track title is required.')
        return t

    def clean_genre(self):
        g = self.cleaned_data.get('genre')
        if not g:
            raise forms.ValidationError('Please select a genre.')
        return g
