from django.conf.urls import patterns, include, url


api_patterns = patterns('',
    url(r'^systems/(\w+)/releases/$', 'stretch.api.release'),
    url(r'^systems/(\w+)/envs/(\w+)/deploy/$', 'stretch.api.deploy'),
)

urlpatterns = patterns('',
    url(r'^api/', include(api_patterns)),
)
