import pymongo
from flask import Flask
from flask.ext.restful import Api

db = pymongo.MongoClient()['stretch-agent']
app = Flask(__name__)
api = Api(app, catch_all_404s=True)
container_dir = '/usr/share/stretch'
agent_dir = '/var/lib/stretch/agent'
task_groups = {}

from stretch.agent import loadbalancers, resources, instances


class TaskException(Exception):
    pass


def run():
    instances.Instance.start_all()
    # TODO: start all load balancers
    app.run(debug=True)


@app.route('/')
def index():
    return 'stretch-agent'
