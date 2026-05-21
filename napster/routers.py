"""
NapsterLegal — Database Router
================================
Handles 3 databases:
  default   → PostgreSQL 17  (primary — all app data)
  replica   → Supabase/PostgreSQL (hot standby — auto-failover via FallbackRouter)
  analytics → MariaDB 11.8  (analytics only — PlayEvent, SearchLog)

OPTION B (ACTIVE — School Project):
  Uses a fallback router: if default DB fails, automatically reads from replica.
  Writes always go to default. Replica is kept in sync via periodic dumps.

OPTION A (COMMENTED — Production):
  Replace this entire file with PostgreSQL Streaming Replication + Patroni.
  Instructions at the bottom of this file.
"""

import logging
logger = logging.getLogger('napster.db')


# ── ANALYTICS ROUTER ─────────────────────────────────────────────────────────
class AnalyticsRouter:
    """
    Routes all analytics app models → MariaDB (analytics database).
    Everything else → PostgreSQL (default).
    """
    ANALYTICS_APPS = {'analytics'}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.ANALYTICS_APPS:
            return 'analytics'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.ANALYTICS_APPS:
            return 'analytics'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        db1 = 'analytics' if obj1._meta.app_label in self.ANALYTICS_APPS else 'default'
        db2 = 'analytics' if obj2._meta.app_label in self.ANALYTICS_APPS else 'default'
        return db1 == db2

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.ANALYTICS_APPS:
            return db == 'analytics'
        if db == 'analytics':
            return False
        return None


# ── FALLBACK ROUTER (OPTION B — ACTIVE) ──────────────────────────────────────
class FallbackRouter:
    """
    OPTION B — School Project High Availability.

    HOW IT WORKS:
    ─────────────
    1. All WRITES always go to 'default' (primary PostgreSQL).
    2. For READS: try 'default' first.
       If default is unreachable (OperationalError), automatically
       fall back to 'replica' (Supabase or second PostgreSQL).
    3. The replica is kept in sync via daily pg_dump + pg_restore (see sync script).

    LIMITATIONS vs Option A:
    - Not real-time replication (daily sync = up to 24h data loss possible)
    - Failover only works for reads, not writes
    - If primary is down, users can still browse but cannot upload/like/comment

    GOOD ENOUGH FOR: School project demonstration.
    NOT GOOD ENOUGH FOR: Production with paying users.

    TO UPGRADE TO OPTION A: See comments at bottom of this file.
    """
    ANALYTICS_APPS = {'analytics'}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.ANALYTICS_APPS:
            return None  # Let AnalyticsRouter handle it

        # Try default, fall back to replica if unavailable
        from django.db import connections
        try:
            connections['default'].ensure_connection()
            return 'default'
        except Exception:
            logger.warning(
                "Primary DB (default) unreachable — falling back to replica for read")
            try:
                connections['replica'].ensure_connection()
                return 'replica'
            except Exception:
                logger.error("Both primary and replica unreachable!")
                return 'default'  # Let Django raise the real error

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.ANALYTICS_APPS:
            return None  # AnalyticsRouter handles this
        return 'default'  # Always write to primary

    def allow_relation(self, obj1, obj2, **hints):
        excluded = self.ANALYTICS_APPS
        if (obj1._meta.app_label in excluded) != (obj2._meta.app_label in excluded):
            return False
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.ANALYTICS_APPS:
            return db == 'analytics'
        if db == 'analytics':
            return False
        if db == 'replica':
            return False  # Never migrate on replica — it gets data via dump/restore
        return db == 'default'


# ══════════════════════════════════════════════════════════════════════════════
# OPTION A — PRODUCTION SETUP (PostgreSQL Streaming Replication + Patroni)
# ══════════════════════════════════════════════════════════════════════════════
#
# When you are ready for production, replace the FallbackRouter above
# with a simple PrimaryRouter (reads + writes always go to 'default').
# Patroni handles the actual failover at the infrastructure level.
#
# STEP-BY-STEP PRODUCTION SETUP:
# ───────────────────────────────
# 1. Provision 2 Ubuntu servers (VPS, AWS EC2, or DigitalOcean Droplets)
#    - Server 1: Primary PostgreSQL  (e.g. 2 CPU / 4GB RAM)
#    - Server 2: Replica PostgreSQL  (same spec)
#
# 2. On both servers:
#    sudo apt install postgresql-17 patroni etcd -y
#
# 3. On Primary — configure postgresql.conf:
#    wal_level = replica
#    max_wal_senders = 3
#    wal_keep_size = 1GB
#    hot_standby = on
#
# 4. Create replication user:
#    CREATE ROLE replicator REPLICATION LOGIN PASSWORD 'strong_password';
#
# 5. Configure pg_hba.conf on Primary to allow replica:
#    host replication replicator <replica_ip>/32 md5
#
# 6. On Replica — initialize from Primary:
#    pg_basebackup -h <primary_ip> -U replicator -D /var/lib/postgresql/17/main -P -Xs -R
#
# 7. Install and configure Patroni on both servers (patroni.yml):
#    scope: napsterlegal
#    name: node1  # or node2
#    etcd:
#      host: 127.0.0.1:2379
#    postgresql:
#      listen: 0.0.0.0:5432
#      connect_address: <this_server_ip>:5432
#      data_dir: /var/lib/postgresql/17/main
#      authentication:
#        replication:
#          username: replicator
#          password: strong_password
#        superuser:
#          username: postgres
#          password: superuser_password
#
# 8. In Django settings.py — use HAProxy or PgBouncer VIP:
#    DATABASES = {
#        'default': {
#            'ENGINE': 'django.db.backends.postgresql',
#            'NAME': 'napsterlegal_db',
#            'USER': 'napster_user',
#            'PASSWORD': '...',
#            'HOST': '<haproxy_ip>',  # HAProxy routes to current primary
#            'PORT': '5432',
#        }
#    }
#    # Remove 'replica' from DATABASES — Patroni handles failover transparently
#
# 9. Use simple PrimaryRouter instead of FallbackRouter:
#    class PrimaryRouter:
#        def db_for_read(self, model, **hints):
#            if model._meta.app_label == 'analytics': return None
#            return 'default'
#        def db_for_write(self, model, **hints):
#            if model._meta.app_label == 'analytics': return None
#            return 'default'
#        def allow_migrate(self, db, app_label, **hints):
#            if app_label == 'analytics': return db == 'analytics'
#            return db == 'default'
#
# 10. Test failover:
#     sudo patronictl -c /etc/patroni.yml failover napsterlegal
#     # Replica becomes primary in < 30 seconds. Zero data loss.
#
# RESULT: True high availability. Automatic failover. Zero data loss.
#         Users experience at most a 30-second pause during failover.
# ══════════════════════════════════════════════════════════════════════════════
