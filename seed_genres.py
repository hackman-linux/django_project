"""
Run this in your Django shell or as a management command:
  python manage.py shell < seed_genres.py

OR copy-paste into: python manage.py shell
"""

from apps.music.models import Genre
from django.utils.text import slugify

GENRES = [
    # Electronic
    ('Electronic',        '#6366F1'),  # indigo
    ('House',             '#8B5CF6'),  # violet
    ('Techno',            '#7C3AED'),  # purple
    ('Drum & Bass',       '#6D28D9'),  # dark violet
    ('Ambient',           '#4F46E5'),  # deep indigo
    ('Trance',            '#818CF8'),  # light indigo
    ('Dubstep',           '#5B21B6'),  # dark purple
    ('EDM',               '#A78BFA'),  # lavender
    ('Lo-Fi',             '#C4B5FD'),  # pale violet
    # Hip-Hop & Urban
    ('Hip-Hop',           '#F59E0B'),  # amber
    ('Rap',               '#D97706'),  # dark amber
    ('Trap',              '#B45309'),  # brown amber
    ('R&B',               '#F97316'),  # orange
    ('Soul',              '#EA580C'),  # dark orange
    ('Funk',              '#C2410C'),  # deep orange
    # Rock & Guitar
    ('Rock',              '#EF4444'),  # red
    ('Alternative',       '#DC2626'),  # dark red
    ('Metal',             '#B91C1C'),  # deep red
    ('Punk',              '#991B1B'),  # darker red
    ('Indie',             '#F87171'),  # light red
    ('Grunge',            '#7F1D1D'),  # maroon
    ('Classic Rock',      '#FCA5A5'),  # pale red
    # Pop & Mainstream
    ('Pop',               '#EC4899'),  # pink
    ('Synth-Pop',         '#DB2777'),  # dark pink
    ('K-Pop',             '#BE185D'),  # deep pink
    ('Dance-Pop',         '#F472B6'),  # light pink
    # Jazz & Classical
    ('Jazz',              '#0EA5E9'),  # sky blue
    ('Blues',             '#0284C7'),  # dark sky
    ('Classical',         '#0369A1'),  # deep sky
    ('Swing',             '#38BDF8'),  # light sky
    ('Bossa Nova',        '#7DD3FC'),  # pale sky
    # World & Afrobeats
    ('Afrobeats',         '#10B981'),  # emerald
    ('Reggae',            '#059669'),  # dark emerald
    ('Reggaeton',         '#047857'),  # deep emerald
    ('Dancehall',         '#34D399'),  # light emerald
    ('Latin',             '#6EE7B7'),  # pale emerald
    ('Afropop',           '#065F46'),  # forest
    ('Highlife',          '#A7F3D0'),  # mint
    ('Afrobeats',         '#10B981'),  # emerald (duplicate guard handled below)
    # African specific
    ('Makossa',           '#14B8A6'),  # teal
    ('Bikutsi',           '#0D9488'),  # dark teal
    ('Ndombolo',          '#0F766E'),  # deep teal
    ('Coupé-Décalé',      '#2DD4BF'),  # light teal
    ('Soukous',           '#5EEAD4'),  # pale teal
    # Country & Folk
    ('Country',           '#F59E0B'),  # amber (lighter)
    ('Folk',              '#92400E'),  # brown
    ('Bluegrass',         '#78350F'),  # dark brown
    ('Acoustic',          '#D97706'),  # amber
    # Gospel & Spiritual
    ('Gospel',            '#FBBF24'),  # yellow
    ('Worship',           '#FCD34D'),  # light yellow
    ('Christian',         '#FDE68A'),  # pale yellow
    # Other
    ('Podcast',           '#64748B'),  # slate
    ('Spoken Word',       '#475569'),  # dark slate
    ('Comedy',            '#94A3B8'),  # light slate
    ('Instrumental',      '#22D3EE'),  # cyan
    ('Experimental',      '#A855F7'),  # purple
    ('Soundtrack',        '#06B6D4'),  # dark cyan
    ('Video Game',        '#0891B2'),  # deeper cyan
]

created = 0
skipped = 0
for name, color in GENRES:
    slug = slugify(name)
    obj, was_created = Genre.objects.get_or_create(
        slug=slug,
        defaults={'name': name, 'color_hex': color}
    )
    if was_created:
        created += 1
        print(f"  ✓ Created: {name}")
    else:
        skipped += 1

print(f"\nDone. {created} genres created, {skipped} already existed.")
print(f"Total genres in DB: {Genre.objects.count()}")
