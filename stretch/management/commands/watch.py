#!/usr/bin/env python
from django.core.management.base import BaseCommand

from stretch import loader
from stretch.sources import AutoloadableSource


class Command(BaseCommand):
    help = 'Monitors autoloading sources'

    def handle(self, *args, **options):
        source, backend = loader.source, loader.backend

        if isinstance(source, AutoloadableSource):
            source.monitor()
