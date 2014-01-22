import multiprocessing


bind = '0.0.0.0:8080'
django_settings = 'stretch.settings'
workers = multiprocessing.cpu_count() * 2 + 1
