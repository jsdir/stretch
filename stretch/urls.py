from django.conf.urls import patterns, include, url


api_patterns = patterns('',
    #get
    url(r'^systems/(\w+)/releases/$', 'stretch.api.index_releases'),
    #post
    url(r'^systems/(\w+)/releases/$', 'stretch.api.create_release'),
    url(r'^systems/(\w+)/envs/(\w+)/deploy/$', 'stretch.api.deploy'),
)

urlpatterns = patterns('',
    url(r'^api/', include(api_patterns)),
)
