# NapsterLegal — Database Backups

Ces fichiers sont générés localement et ne sont PAS commités dans le repo (voir .gitignore).
Après avoir cloné le projet, régénère-les depuis Parrot OS ou restaure-les depuis une source fiable.

## Fichiers

| Fichier | Base | Moteur | Usage |
|---|---|---|---|
| `napsterlegal_primary.dump` | napsterlegal_db | PostgreSQL 17 · port 5432 | Primary — toutes les données app |
| `napsterlegal_analytics.sql` | napsterlegal_analytics | MariaDB 11.8 · port 3306 | Analytics — PlayEvent, SearchLog |

## Régénérer les dumps (sur Parrot OS)

```bash
cd ~/envs/django_project
pg_dump -U napster_user -h localhost -p 5432 \
  -d napsterlegal_db -F c \
  -f backups/napsterlegal_primary.dump

mysqldump -u root -p napsterlegal_analytics \
  > backups/napsterlegal_analytics.sql
```

## Restaurer sur Windows (Option B)

Voir le guide complet : `docs/windows_setup.md`

### PostgreSQL primary (port 5432)
```powershell
pg_restore -U napster_user -p 5432 -d napsterlegal_db -v backups\napsterlegal_primary.dump
```

### PostgreSQL replica (port 5433) — même dump
```powershell
pg_restore -U napster_user -p 5433 -d napsterlegal_db -v backups\napsterlegal_primary.dump
```

### MariaDB analytics (port 3306)
```powershell
mysql -u root -p napsterlegal_analytics < backups\napsterlegal_analytics.sql
```

## Architecture (Option B — School Project)
