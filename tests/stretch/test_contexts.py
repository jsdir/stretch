from mock import Mock
from nose.tools import eq_

from stretch import contexts


def test_plugin_context():
    deploy = Mock()
    context = contexts.plugin_context(deploy)
    eq_(context['config'], deploy.environment.config)
    eq_(context['environment'], deploy.environment.name)
    eq_(context['release'], deploy.release.name)
    eq_(context['release_sha'], deploy.release.sha)
    eq_(context['existing_release'], deploy.existing_release.name)
    eq_(context['existing_release_sha'], deploy.existing_release.sha)
