from __future__ import absolute_import

# Requires working docker installation
from server import InstanceSupervisor


class TestSupervisor(TestCase):
    @slow # Check for docker first
    def test_check_instances():
        # Test with multiple instances
        # start with mock db and a running container (busybox)
        #  - download this if we have to
        # kill instance (docker kill)
        # wait .5s or none
        # assert instance running again

    @slow # possibly, look again
    def test_start_instance(self):
        pass

    @slow # possibly, look again
    def test_stop_instance(self):
        pass