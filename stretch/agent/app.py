import pymongo
from flask import Flask
from flask.ext.restful import Api


db = pymongo.MongoClient()['stretch-agent']
app = Flask(__name__)
api = Api(app, catch_all_404s=True)
container_dir = '/usr/share/stretch'
agent_dir = '/var/lib/stretch/agent'


class TaskException(Exception):
    pass
