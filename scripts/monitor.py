#!/usr/bin/env python
import stretch
from stretch.sources import AutoloadableSource


source, backend = stretch.source, stretch.backend

if isinstance(source, AutoloadableSource):
    source.monitor()
