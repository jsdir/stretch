import pymongo
from flask import Flask
from flask.ext.restful import Api

class TaskException(Exception):
    pass

#from stretch.agent import loadbalancers, instances


db = pymongo.MongoClient()['stretch-agent']
app = Flask(__name__)
api = Api(app, catch_all_404s=True)
container_dir = '/usr/share/stretch'
agent_dir = '/var/lib/stretch/agent'
task_groups = {}


#def run():
#    instances.Instance.start_all()
#    loadbalancers.LoadBalancer.start_all()
#    app.run()


@app.route('/')
def index():
    return 'stretch-agent'
