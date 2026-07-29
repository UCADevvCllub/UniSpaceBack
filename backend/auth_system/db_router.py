class LogsRouter:
    """
    Database router that ensures APILog model lives strictly in 'logs_db'
    and prevents application tables (like Event, TVBooking, UserAccount) 
    from being created inside logs.sqlite3.
    """
    def db_for_read(self, model, **hints):
        if model._meta.model_name == 'apilog':
            return 'logs_db'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.model_name == 'apilog':
            return 'logs_db'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._meta.model_name == 'apilog' or obj2._meta.model_name == 'apilog':
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == 'logs_db':
            # Only allow apilog model in logs_db
            return model_name == 'apilog'
        elif model_name == 'apilog':
            # Do NOT migrate apilog into default database
            return False
        return None
