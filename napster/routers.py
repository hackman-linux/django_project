class AnalyticsRouter:
    """
    Routes all models in the 'analytics' app to MariaDB.
    Everything else goes to PostgreSQL (default).
    """
    ANALYTICS_APPS = {'analytics'}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.ANALYTICS_APPS:
            return 'analytics'   # --> MariaDB
        return 'default'         # --> PostgreSQL

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.ANALYTICS_APPS:
            return 'analytics'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        # Allow relations within the same database
        db_set = {'analytics'}
        if obj1._meta.app_label in db_set or obj2._meta.app_label in db_set:
            return obj1._meta.app_label == obj2._meta.app_label
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.ANALYTICS_APPS:
            return db == 'analytics'
        return db == 'default'
