"""
Service to ensure that all instances are running and discoverable.
"""
from stretch import utils
from stretch.agent.instances import Instance


while True:
    cids = utils.run_cmd(['docker', 'ps', '-q']).splitlines()
    for instance in Instance.get_instances():
        cid = instance.data['cid']
        if cid in cids:
            # Instance is running
            # Set endpoint key
            instance.set_endpoint()
        else:
            # Instance is down
            instance.data['cid'] = None
            instance.data['endpoint'] = None
            instance.save()
            # Log the event and start the instance
            instance.start()


