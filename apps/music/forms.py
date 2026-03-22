from django import forms
from .models import Track, Album, Genre


class TrackUploadForm(forms.ModelForm):
    class Meta:
        model  = Track
        fields = ['title', 'audio_file', 'cover_image', 'genre', 'album',
                  'lyrics', 'bpm', 'license_type', 'is_explicit', 'is_published',
                  'preview_start']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'input-field',
                'placeholder': 'Track title'
            }),
            'audio_file': forms.FileInput(attrs={
                'class': 'input-field',
                'accept': 'audio/mpeg,audio/flac,audio/wav,audio/*'
            }),
            'cover_image': forms.FileInput(attrs={
                'class': 'input-field',
                'accept': 'image/*'
            }),
            'genre': forms.Select(attrs={'class': 'input-field'}),
            'album': forms.Select(attrs={'class': 'input-field'}),
            'lyrics': forms.Textarea(attrs={
                'class': 'input-field',
                'rows': 6,
                'placeholder': 'Paste your lyrics here (optional)'
            }),
            'bpm': forms.NumberInput(attrs={
                'class': 'input-field',
                'placeholder': 'e.g. 128'
            }),
            'license_type': forms.Select(attrs={'class': 'input-field'}),
            'preview_start': forms.NumberInput(attrs={
                'class': 'input-field',
                'placeholder': 'Preview start in seconds (default: 0)'
            }),
        }
