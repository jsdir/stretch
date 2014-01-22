import json
from mock import Mock, PropertyMock, patch
from django.test import TestCase
from django.test.client import Client

from stretch.models import System, Environment, Release
from stretch import api


class TestApi(TestCase):
    def setUp(self):
        self.client = Client()

        self.system = System(name='sys')
        self.system.save()

        self.env = Environment(name='env')
        self.env.system = self.system
        self.env.save()

        self.release = Release(pk=1, tag='123')
        self.release.system = self.system
        self.release.save()

    def testIndexReleases(self):
        response = self.client.get('/api/systems/a/releases/?tag=124')
        self.assertEquals(response.status_code, 404)

        response = self.client.get('/api/systems/sys/releases/?tag=124')
        self.assertEquals(response.status_code, 404)

        response = self.client.get('/api/systems/sys/releases/?tag=123')
        self.assertEquals(json.loads(response.content), {'id': 1})

    @patch('stretch.models.System.source', new_callable=PropertyMock)
    def testCreateRelease(self, source_property):
        source = Mock()
        source.pull.return_value = ('path', '12345')
        source_property.return_value = source

        data = {'options': json.dumps({'foo': 'bar'})}
        response = self.client.post('/api/systems/sys/releases/', data=data)
        release = Release.objects.get(pk=json.loads(response.content)['id'])

        source.pull.assert_called_with({'foo': 'bar'})
        self.assertEquals(release.tag, '12345')

    '''
    def testDeploy(self):
        response = self.client.get('/api/systems/none/release')
        self.assertEquals(response.status_code, 404)

        response = self.client.get('/api/systems/sys/release')
        self.assertEquals(response.status_code, 404)

        response = self.client.get('/api/systems/sys/release')
    '''
