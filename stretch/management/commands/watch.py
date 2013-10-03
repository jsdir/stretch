#!/usr/bin/env python
from django.core.management.base import BaseCommand
import time

from stretch import sources


class Command(BaseCommand):
    help = 'Watches autoloadable sources for file changes'

    def handle(self, *args, **options):
        sources.watch()

        # Keep running event loop
        while True:
            time.sleep(5)
