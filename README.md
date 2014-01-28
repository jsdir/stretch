stretch
=======

A simple PaaS powered by [docker](https://github.com/dotcloud/docker).

[![Build Status](https://travis-ci.org/gatoralli/stretch.png?branch=refactor)](https://travis-ci.org/gatoralli/stretch)
[![Coverage Status](https://coveralls.io/repos/gatoralli/stretch/badge.png?branch=refactor)](https://coveralls.io/r/gatoralli/stretch)


Installation
------------


Usage
-----

1. Use the commands.


Commands
--------

###create

####release

- system: `stretch create system [system]`
- environment: `stretch create environment [system]/[environment]`
- group: `stretch create group [system]/[environment]/[group] [node] --amount [initial_amount]`
- release: `stretch create release [source] --source_key value`


To create a release from our Git source:

```sh
$ stretch create release the_source
1bde9201
# Returns the id of the new release
```


###destroy

Destroy objects

```sh
# Destroy a system...
$ stretch destroy system [system]

# Destroy an environment...
$ stretch destroy environment [system]/[environment]

# Destroy a group...
$ stretch destroy group [system]/[environment]/[group]
```

###deploy

Releases can be deployed to environments.

```sh
$ stretch deploy [release_id] [system]/[environment]
```

So, continuing with our example...

```sh
$ stretch deploy 1bde9201 sys/1
```

We can also use the release name instead of the id.

```sh
$ stretch deploy spicy-river-0e4a sys/1
```


###scale

Stretch can scale groups.

- up: `stretch scale [system]/[environment]/[group] up [amount]`
- down: `stretch scale [system]/[environment]/[group] down [amount]`
- to: `stretch scale [system]/[environment]/[group] to [amount]`

```sh
# Scale up
$ stretch scale sys1/production/web up 10

# Scale down
$ stretch scale sys1/production/messaging down 3

# Scale to an amount
$ stretch scale sys1/staging/worker to 4
```

Add the `--routing` option to scale the routing group.

```sh
# Scale the routing group
$ stretch scale sys1/production/web to 4 --routing
```


###ls

Stretch can display objects with nested relationships.

With the `ls` command, we can list releases,

```sh
$ stretch ls --releases
- releases:
  - spicy-river-0e4a [1bde9201] (created 11 minutes ago)
  - rolling-log-64bd [e91aa6c8] (created 4 days ago)
```

systems,

```sh
$ stretch ls --systems
- systems:
  - sys1
  - sys2
```

environments in a system,

```sh
$ stretch ls sys1
- [system] environments:

  - production [sys1/production]
  | - Current release: spicy-river-0e4a [1bde9201]
  | - Groups:
  |   - web [sys1/production/web]
  |     - 10 hosts
  |     - 4 routers
  |   - worker [sys1/production/worker]
  |     - 4 instances
  |     - 0 routers
  |   - messaging [sys1/production/messaging]
  |     - 1 instance
  |     - 0 routers

  - staging [sys1/staging]
  | - Current release: spicy-river-0e4a [1bde9201]
  | - Previous release: rolling-log-64bd [023a7c2d]
  | - Groups:
  |   - web [sys1/staging/web]
  |     - 10 hosts
  |     - 4 routers
  |   - worker [sys1/staging/worker]
  |     - 4 instances
  |     - 0 routers
  |   - messaging [sys1/staging/messaging]
  |     - 1 instance
  |     - 0 routers
```

groups in an environment,

```sh
$ stretch ls sys1/production
- production [sys1/production]
| - Current release: spicy-river-0e4a [1bde9201]
| - Groups:
|   - web [sys1/production/web]
|     - 10 hosts
|     - 4 routers
|   - worker [sys1/production/worker]
|     - 4 instances
|     - 0 routers
|   - messaging [sys1/production/messaging]
|     - 1 instance
|     - 0 routers
```

and a group's hosts and routers.

```sh
$ stretch ls sys1/production/web
- web [sys1/production/web]

  - Hosts [10]:

    - 30.24.135.2
    - 30.24.135.3
    - 30.24.135.4
    - 30.24.135.5
    - 30.24.135.6
    - 30.24.135.7
    - 30.24.135.8
    - 30.24.135.9
    - 30.24.135.10
    - 30.24.135.11

  - Routers [4]:

    - 132.53.52.32
    - 132.53.52.35
    - 132.53.3.156
    - 132.53.3.157
```


Notes
-----
- Routing group is created and destroyed alongside the group it routes to. It is virtually invisible to the client except when it is scaled.
