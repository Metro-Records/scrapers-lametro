import logging
import os

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration


if SENTRY_DSN := os.getenv("SENTRY_DSN", False):
    sentry_logging = LoggingIntegration(level=logging.INFO, event_level=logging.FATAL)

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), sentry_logging],
        environment=os.getenv("SENTRY_ENVIRONMENT", "dev"),
    )

CACHE_DIR = "/tmp/cache/_cache"
SCRAPED_DATA_DIR = "/tmp/cache/_data"
STATIC_ROOT = "/tmp"

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgis://opencivicdata:@localhost/opencivicdata"
)

INSTALLED_APPS = (
    "django.contrib.contenttypes",
    "opencivicdata.core.apps.BaseConfig",
    "opencivicdata.legislative.apps.BaseConfig",
    "councilmatic_core",
    "pupa",
)
OCD_CITY_COUNCIL_NAME = None

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)s %(name)s: %(message)s",
            "datefmt": "%m/%d/%Y %H:%M:%S",
        }
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "class": "pupa.ext.ansistrm.ColorizingStreamHandler",
            "formatter": "standard",
        },
    },
    "loggers": {
        "": {"handlers": ["default"], "level": "DEBUG", "propagate": True},
        "scrapelib": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "requests": {"handlers": ["default"], "level": "WARN", "propagate": False},
        "boto": {"handlers": ["default"], "level": "WARN", "propagate": False},
    },
}
