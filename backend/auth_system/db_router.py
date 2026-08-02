class LogsRouter:
    """
    Database router that ensures APILog and APISQLLog models live strictly in 'logs_db'
    and prevents application tables (like Event, TVBooking, UserAccount) 
    from being created inside logs.sqlite3.
    """
    def db_for_read(self, model, **hints):
        if model._meta.model_name in ('apilog', 'apisqllog'):
            return 'logs_db'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.model_name in ('apilog', 'apisqllog'):
            return 'logs_db'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._meta.model_name in ('apilog', 'apisqllog') or obj2._meta.model_name in ('apilog', 'apisqllog'):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == 'logs_db':
            # Only allow apilog and apisqllog models in logs_db
            return model_name in ('apilog', 'apisqllog')
        elif model_name in ('apilog', 'apisqllog'):
            # Do NOT migrate log models into default database
            return False
        return None

