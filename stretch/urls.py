from django.conf.urls import patterns, include, url
from stretch.api import MySseStreamView


api_patterns = patterns('',
    url(r'^systems/(\w+)/releases/$', 'stretch.api.index_releases'),
    url(r'^systems/(\w+)/envs/(\w+)/deploy/$', 'stretch.api.deploy'),
    url(r'^test/(\w+)/$', 'stretch.api.lol')
)

urlpatterns = patterns('',
    url(r'^api/', include(api_patterns)),
)
