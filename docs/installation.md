# Installation

## Etcd Server
Using etcd, the stretch system, along with instances, can access realtime configuration and service data.

1. Start etcd entrypoint on a machine accessible by the master and all hosts. The entrypoint should usually run on the stretch master.

    stretch-master$ etcd -f -name node0 -data-dir node0 -cert-file=./fixtures/ca/server.crt -key-file=./fixtures/ca/server.key.insecure

2. Set the public location of the entrypoint in local_settings.py as ETCD_HOST
3. Start the docker registry on a machine accessible by the master, all hosts, and developer machines.

