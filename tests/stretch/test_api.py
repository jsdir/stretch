from django.utils.unittest import TestCase
from django.test.client import Client

from stretch import api


class TestApi(TestCase):
    def setUp(self):
        self.client = Client()

    def testIndexReleases(self):
        response = self.client.get('/api/systems/sys/releases/?tags=123')

        self.assertEquals(response.code, 200)

    def testDeploy(self):
        response = self.client.get('/api/systems/sys/releas')
        self.assertEquals(response.code, 200)


Environment.deploy.delay(release)
# Start streaming websocket
