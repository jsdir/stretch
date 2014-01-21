from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^api/systems/(\w+)/releases/$', 'api.get_releases'),
    url(r'^api/systems/(\w+)/deploy/$', 'api.deploy'),
)
