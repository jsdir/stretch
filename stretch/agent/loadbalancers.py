from flask.ext.restful import reqparse, Resource

from stretch.agent.loadbalancer_server import get_client
from stretch.agent import api, resources, db


class LoadBalancer(resources.PersistentObject):
    name = 'loadbalancer'

    @classmethod
    def create(cls, args):
        super(LoadBalancer, self).create(args)
        self.start()

    def delete(self):
        db.endpoints.remove({'lb_id': self.data['_id']})
        self.stop()
        super(Instance, self).delete()

    def start(self):
        get_client().start_lb(self.data['_id'])

    def stop(self):
        get_client().stop_lb(self.data['_id'])

    @classmethod
    def start_all(cls):
        [lb.start() for lb in cls.get_lbs()]

    @classmethod
    def get_lbs(cls):
        for lb in self.collection.find(fields=['_id']):
            yield cls(lb['_id'])
