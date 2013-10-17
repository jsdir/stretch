# Stretch Agent

The stretch agent is a daemon that runs on every host controlled by stretch. The agent is responsible for managing, running, stopping, deploying, and switching nodes on a host.

On the node's host, the `stretch` minion module interfaces with the agent.

A file buffer is used to handle the `files`, `templates`, and configurations.

Uses a:
 - {instance: active_configuration} state

The agent should not know about environments, except during deploys.
It should maintain a collection of instances.
