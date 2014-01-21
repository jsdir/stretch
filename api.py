from django.http import HttpResponse
import time


def on_push(a):
    return HttpResponse("<h1>He</h1>" + str(a))
