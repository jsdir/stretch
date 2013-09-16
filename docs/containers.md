# Containers

Stretch uses docker containers for shipping application releases from source to backend. They are an important part of the [Stretch Pipeline](pipeline.md). Docker containers in stretch are usually defined with a `container.yml`, `files` directory, `templates` directory, `app` directory, and a standard `Dockerfile`.

#### container.yml
The `Dockerfile` is the standard way to automate the container-building process. However, it lacks the abstraction needed for use in stretch. The `container.yml` file complements the `Dockerfile` by giving supplying the official container name along with the location of any image the container depends upon. The `Dockerfile` used for the build should be included in the same directory as the `container.yml`.

```yaml
dockerfile: Dockerfile
name: node_name
from: ../relative/path/to/the/base/image/container.yml
```

- `dockerfile` is the relative path to the Dockerfile that builds the image. By default, the value is `Dockerfile`.

- `name` is the name stretch should use when pushing the container to the registry. By default, this value is this container's node's name.

- `from` is the relative path to the `container.yml` of the base image that this container will depend upon, if it uses any base image at all. By default, this key is not used and the container being built is assumed not to require any base image.

#### files/
The `files` directory should contain all static files that will be added to the container.

#### templates/
The `templates` directory should contain all template files that will be deployed to the container. All template files should be jinja templates. These templates will be compiled with the [Application Context](template_contexts.md). No extra file extension should be used because the files will be compiled in place. The template compilation process is perfomed by the [Stretch Agent](agent.yml).

#### app/
The `app` directory should contain the core application for the container. Since the `app` directory is added into the docker container, every time the conatiner is restarted, the `app` directory is reset. Because of this, nothing in this directory should be expected to persist. This is not a place for databases or any other form of changing data.

#### Dockerfile

Using this source:

    source/
        stretch.yml
        config.yml
        secrets.yml

        Dockerfile
        container.yml
        templates/
        files/
        app/

Here is a common template for `Dockerfile`s used with stretch:

```bash
FROM system_name/base
# or FROM <image>:<tag>

# Install requirements
RUN apt-get update

ADD files /home/stretch/files
ADD app /home/stretch/app

# Link different files to different locations

# Run application
```
