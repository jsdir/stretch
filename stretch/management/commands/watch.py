#!/usr/bin/env python
from django.core.management.base import BaseCommand

import stretch
from stretch.sources import AutoloadableSource


class Command(BaseCommand):
    help = 'Monitors autoloading sources'

    def handle(self, *args, **options):
        source, backend = stretch.source, stretch.backend

        if isinstance(source, AutoloadableSource):
            source.monitor()
