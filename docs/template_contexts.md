# Tempalte Contexts

Template contexts are groups of variables that can be used to compile templates. Two template contexts are used within the [Stretch Pipeline](pipeline.md): the deploy and application contexts.

## Deploy Context

During the *Pull release configuration* stage of the *deploy* step of the Stretch Pipeline, the release configuration is parsed and compiled with the deploy context. The deploy context gives dynamic access to the state of the environment and release at deploy time.

Several variables are inside this context, and they can be use to create flexible configuration.

- `services` provides an accessible way to interact with services defined in stretch.

```yaml
mysql_service: {{ services.mysql }}
service_options: {{ services.myservice.option }}
```

- `environment` evaluates as the name of the environment being deployed to, but also serves as the environment object used by the ORM.

It can be used both ways:

```yaml
{% if environment == 'production' %}
special_option: production_value
{% endif %}

hostnames:
    hostnames_option: {{ environment.hosts.get_hostnames('*') }}
```

- `release` is the object of the release being deployed.

```yaml
release_options:
    sha: {{ release.sha }}
    id: {{ release.id }}
    name: {{ release.name }}

new_release: {{ release }}
```

- `existing_release` is the object of the release being replaced in the current environment.

## Application Context

The application context is used by the [Stretch Agent](agent.md) when compiling templates for a [Container](containers.md).

The several variables used inside this context can be used to change files for every deploy.

- `environment` is the the name of the environment being deployed to. Unlike the deploy context, the `environment` variable in this context is a string, and it provides no methods to access the environment's child objects.

- `config` is the node's generated configuration tree.

- `node` is the node object that is being deployed to.

- `release` and `existing_release` can be used the same way in this context as in the deploy context.
