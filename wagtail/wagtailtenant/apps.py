from django.apps import AppConfig, apps
from django.conf import settings
from django.core.checks import Critical, Error, Warning, register
from django.core.files.storage import default_storage
from wagtail.wagtailtenant.storage import TenantStorageMixin
from wagtail.wagtailtenant.utils import get_public_schema_name, get_tenant_model


class WagtailTenantConfig(AppConfig):
    name = 'wagtail.wagtailtenant'
    label = 'wagtailtenant'
    verbose_name = "Wagtail tenant"

@register('config')
def best_practice(app_configs, **kwargs):
    """
    Test for configuration recommendations. These are best practices, they
    avoid hard to find bugs and unexpected behaviour.
    """
    if app_configs is None:
        app_configs = apps.get_app_configs()

    # Take the app_configs and turn them into *old style* application names.
    # This is what we expect in the SHARED_APPS and TENANT_APPS settings.
    INSTALLED_APPS = [
        config.name
        for config in app_configs
    ]

    if not hasattr(settings, 'TENANT_APPS'):
        return [Critical('TENANT_APPS setting not set')]

    if not hasattr(settings, 'TENANT_MODEL'):
        return [Critical('TENANT_MODEL setting not set')]

    if not hasattr(settings, 'SHARED_APPS'):
        return [Critical('SHARED_APPS setting not set')]

    if 'wagtail.wagtailtenant.routers.TenantSyncRouter' not in settings.DATABASE_ROUTERS:
        return [
            Critical("DATABASE_ROUTERS setting must contain "
                     "'wagtail.wagtailtenant.routers.TenantSyncRouter'.")
        ]

    errors = []

    django_index = next(i for i, s in enumerate(INSTALLED_APPS) if s.startswith('django.'))
    if INSTALLED_APPS.index('wagtail.wagtailtenant') > django_index:
        errors.append(
            Warning("You should put 'wagtail.wagtailtenant' before any django "
                    "core applications in INSTALLED_APPS.",
                    obj="django.conf.settings",
                    hint="This is necessary to overwrite built-in django "
                         "management commands with their schema-aware "
                         "implementations.",
                    id="wagtailtenant.W001"))

    if not settings.TENANT_APPS:
        errors.append(
            Error("TENANT_APPS is empty.",
                  hint="Maybe you don't need this app?",
                  id="wagtailtenant.E001"))

    if hasattr(settings, 'PG_EXTRA_SEARCH_PATHS'):
        if get_public_schema_name() in settings.PG_EXTRA_SEARCH_PATHS:
            errors.append(Critical(
                "%s can not be included on PG_EXTRA_SEARCH_PATHS."
                % get_public_schema_name()))

        # make sure no tenant schema is in settings.PG_EXTRA_SEARCH_PATHS
        invalid_schemas = set(settings.PG_EXTRA_SEARCH_PATHS).intersection(
            get_tenant_model().objects.all().values_list('schema_name', flat=True))
        if invalid_schemas:
            errors.append(Critical(
                "Do not include tenant schemas (%s) on PG_EXTRA_SEARCH_PATHS."
                % ", ".join(sorted(invalid_schemas))))

    if not settings.SHARED_APPS:
        errors.append(
            Warning("SHARED_APPS is empty.",
                    id="wagtailtenant.W002"))

    if not set(settings.TENANT_APPS).issubset(INSTALLED_APPS):
        delta = set(settings.TENANT_APPS).difference(INSTALLED_APPS)
        errors.append(
            Error("You have TENANT_APPS that are not in INSTALLED_APPS",
                  hint=[a for a in settings.TENANT_APPS if a in delta],
                  id="wagtailtenant.E002"))

    if not set(settings.SHARED_APPS).issubset(INSTALLED_APPS):
        delta = set(settings.SHARED_APPS).difference(INSTALLED_APPS)
        errors.append(
            Error("You have SHARED_APPS that are not in INSTALLED_APPS",
                  hint=[a for a in settings.SHARED_APPS if a in delta],
                  id="wagtailtenant.E003"))

    if not isinstance(default_storage, TenantStorageMixin):
        errors.append(Warning(
            "Your default storage engine is not tenant aware.",
            hint="Set settings.DEFAULT_FILE_STORAGE to "
                 "'wagtail.wagtailtenant.storage.TenantFileSystemStorage'",
            id="wagtailtenant.W003"
        ))

    return errors
