from django.apps import AppConfig


class ClinicConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'clinic'

    def ready(self):
        # Install triggers _after_ migrations run, not at import time.
        from django.db.models.signals import post_migrate
        from .db_utils import init_triggers

        def _install_triggers(sender, **kwargs):
            init_triggers()

        post_migrate.connect(_install_triggers, sender=self)