from django.conf.urls import patterns, url, include
from rest_framework import routers

from api import views


router = routers.DefaultRouter()
router.register('environments', views.EnvironmentViewSet)

urlpatterns = patterns('',
    url('^', include(router.urls))
)
