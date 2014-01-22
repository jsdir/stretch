from django.utils.unittest import TestCase
from django.test.client import Client

from stretch import api


class TestApi(TestCase):
    def setUp(self):
        self.client = Client()

    def testIndexReleases(self):
        response = self.client.get('/api/systems/sys/releases/?tags=123')

        self.assertEquals(response.code, 200)

    def testCreateRelease(self):
        raise Exception()

    def testDeploy(self):
        response = self.client.get('/api/systems/sys/release')
        self.assertEquals(response.code, 200)
