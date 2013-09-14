# Build Files

The build files are a collection of declarative, stretch-specific files used for every release. Together, they allow much of the environment infrastructure to be managed in version control via sources. Because of the tight integration between build files and the [Stretch Pipeline](stretch_pipeline.md), deploys and rollbacks are made much more declarative.

Build files describe nodes, their locations, configurations, and plugins. Different kinds of build files are used because of these different delegations. Build files are flexible enough to completely handle encryption, flexible template compiling, and use in the different stages of the Stretch Pipeline.

## Node Declarations

A source can use either single or multiple node declarations. The single node declaration uses the node defined in the root directory while the multiple node declaration uses the nodes defined in multiple subdirectories.

For both types of declaration, three build files are used: `stretch.yml`, `config.yml`, and `secrets.yml`.

## Declaration Structure

### Individual Node Declaration

For individual node declaration, the node is defined in the source root. All three build files are included in the source root because they define that node. Each build file has a different role in the application of an individual node declaration.

    source/
        stretch.yml
        config.yml
        secrets.yml
        Dockerfile
        container.yml
        templates/
        files/
        app/

#### stretch.yml
`stretch.yml` defines data used for the build step of the Stretch Pipeline.

```yaml
container: path/to/container.yml

plugins:
    plugin_name:
        option: value
```

- `container` defines the [Container](container.md) that the node should use. By default, the value is `container/container.yml`.

- `plugins` is a tree of Deploy Plugins that will be executed when the node is deployed.

#### config.yml
`config.yml` defines node-specific configuration.

```yaml
app_name: FooBar

mysql: {{ services.mysql }}
rabbitmq: {{ services.rabbitmq }}

app_password: !secret passwords.app_password
```

As shown above with the `mysql` and `rabbitmq` keys, `config.yml` can written as a jinja template using the the [Deploy Context](template_contexts.md). Secret data can also be inserted using the `!secret` tag.

#### secrets.yml
`secrets.yml` stores sensitive information that can be accessed by the `config.yml` build file. The reason secret data and configuration are separated into different files is that decryption and template compilation happen at two completely different times in the Stretch Pipeline.

```yaml
passwords:
    app_password: !encrypted |-
        = encrypted password =
    foo_password: !encrypted |-
        = another encrypted password =
```

### Multiple Node Declaration

For multiple node declaration, the nodes are defined in multiple subdirectories. The three build files are used for both local and global node configuration.

    source/
        stretch.yml
        config.yml
        secrets.yml
        containers/
            base/
                Dockerfile
                container.yml
        node_1/
            stretch.yml
            config.yml
            secrets.yml
            Dockerfile
            container.yml
            templates/
            files/
            app/
        node_2/
            stretch.yml
            config.yml
            secrets.yml
            Dockerfile
            container.yml
            templates/
            files/
            app/

`node_1` and `node_2` with their build files are treated like individual nodes and are expected to used individual node declaration. Only the root build files (`source/stretch.yml`, `source/config.yml`, and `source/secrets.yml`) are different.

#### stretch.yml
`source/stretch.yml` is a root build file. The only difference between this file and the `stretch.yml` used in individual node declaration is that the `nodes` block is used instead of the `container` key, the `plugins` block operates differently, a `local_stretch` block is used.

```yaml
nodes:
    web: node_1
    worker: node_2
    node_name: path/to/node

plugins:
    plugin_name:
        option: value

local_stretch:
    configuration_name:
        includes:
            - web
            - worker
        plugins:
            plugin_name:
                option: value

container: path/to/container.yml

plugins:
    plugin_name:
        option: value
```

- `nodes` defines the names and locations of the different nodes in the source.

- Unlike the `plugins` block used for individual node declaration, the `plugins` block used here defines Build Plugins rather than Deploy Plugins.

- the `local_stretch` block provides a way to define individual node declaration for multiple nodes at once. The `includes` key contains a list of the nodes that will use that global configuration.

#### config.yml
`source/config.yml` defines global configuration for all nodes. It can used as a jinja template and can reference secret data just like in individual node declaration.

```yaml
config:
    global_configuration_options: value
    global_service: {{ services.service_used_by_all_nodes }}
    password: !secret passwords.global_password

local_config:
    includes:
        - web
        - worker
    config:
        node_service: {{ services.service_used_by_some_nodes }}
        database_password: !secret some.database.password
```

- The `config` block contains global configuration that is applied to all nodes.

- The `local_config` block can apply configuration to a list of nodes specified in the `includes` list.

#### secrets.yml
Just like with individual node declaration, `source/secrets.yml` stores sensitive information that can be accessed by the root `config.yml` build file.


### Why not use services for everything?

Services are useful for configuration that is independent of the system's development cycle. Because services have no versions, environment rollbacks will have no effect on them. A service for an external database solution may change a port, address, or API key during the development cycle. When a rollback is issued, the service should continue to use the same current port, address, and API key instead of the now-defunct credentials existent at the time of that release. Services should not revert to their state during a previous release. These are the scenarios for which services were created.

Internal configuration such as passwords for applications in nodes are more practically defined within build files rather than external services. This internal configuration changes along with the system's development cycle, and this data needs to be reverted to on rollback or changed on deploy. 
