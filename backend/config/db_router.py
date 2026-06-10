class ReadReplicaRouter:
    """Route reads to the replica, writes to the primary.

    Active only when REPLICA_URL is set (see settings). Relations are
    allowed because both aliases point at the same physical dataset.
    """

    def db_for_read(self, model, **hints):
        return "replica"

    def db_for_write(self, model, **hints):
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db == "default"
