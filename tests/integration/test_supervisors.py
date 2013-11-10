from mock import Mock, patch
import time
from nose.twistedtools import reactor, stop_reactor

from stretch.agent import supervisors


"""
@patch('stretch.models.LoadBalancer.objects.all', Mock())
def test_endpoint_supervisor():
    lb = Mock()
    lb.group = group = Mock()
    models.LoadBalancer.objects.all.return_value = [lb]
    
    #reactor, reactor_thread = threaded_reactor()
    supervisors.run_endpoint_supervisor(reactor)
    time.sleep(1)
    reactor.stop()
"""
