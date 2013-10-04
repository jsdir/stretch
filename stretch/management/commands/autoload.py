#!/usr/bin/env python
from django.core.management.base import BaseCommand
import time

from stretch import sources, signals


class Command(BaseCommand):
    help = 'Syncs autoloadable sources to their environments'

    def handle(self, *args, **options):
        signals.load_sources.send(sender=self)
        sources.watch()

        # Keep running event loop
        while True:
            time.sleep(5)
