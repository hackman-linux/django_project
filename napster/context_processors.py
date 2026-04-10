def language_options(request):
    """Provides language choices to every template."""
    return {
        'lang_options': [
            ('en', 'English',   '🇬🇧'),
            ('fr', 'Français',  '🇫🇷'),
            ('es', 'Español',   '🇪🇸'),
            ('de', 'Deutsch',   '🇩🇪'),
            ('pt', 'Português', '🇵🇹'),
        ]
    }

def site_name(request):
    return {'SITE_NAME': 'NapsterLegal'}
