from dishka import AsyncContainer, Provider, Scope, from_context, make_async_container
from dishka.integrations.fastapi import FastapiProvider

from app.core.config import Settings
from app.core.db import DbProvider
from app.modules.auth.providers import AuthProvider
from app.modules.progress.providers import ProgressProvider


class ConfigProvider(Provider):
    settings = from_context(provides=Settings, scope=Scope.APP)


def build_container(settings: Settings, *overrides: Provider) -> AsyncContainer:
    return make_async_container(
        ConfigProvider(),
        DbProvider(),
        AuthProvider(),
        ProgressProvider(),
        FastapiProvider(),
        *overrides,
        context={Settings: settings},
    )
