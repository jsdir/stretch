# Stretch Pipeline

The stretch pipeline moves apps and their configurations from sources to the backend. There are many stages in the pipeline, each allowing a degree of configuration and flexibility. Essentially, the pipeline consists of two major steps: `build` and `deploy`. The output for both of these steps are logged for realtime display in the web client. 


## Build

The `build` step builds a release by pulling apps and their configurations from sources, archiving the apps and configurations, running build plugins, building docker images for the apps, and pushing the newly-built images to the private registry.

The stages of the build step:

  1. Pull from sources
  2. Decrypt
  3. Archive
  4. Build
  5. Push
  6. Run build plugins

### Pull from sources
Code is pulled from all defined sources and placed in a temporary folder called the buffer. The buffer is structured in a way to keep multiple sources separate and to preserve source priority.

    buffer/
        1/
            data.dat
            config.yml
        2/
            config.yml
            foo.bar
        3/
            bar.foo
            data.dat

At every opportunity, sources with higher numbers overwrite sources with lower numbers. Source `3`'s `data.dat` will overwrite source `1`'s `data.dat`. This source priority is determined by the order of source declaration in the stretch configuration. Sources defined later override sources defined earlier.

### Decrypt
The buffer is checked for stretch configuration files. These files are parsed in order to find all secret configuration data and encrypted files which are then decrypted with the private key. Decrypted configuration data is inserted into normal configuration data with the use of the `encrypted` directive.

Decryption takes place before archiving because the private key is assumed to be ephemeral. Rollbacks and other deploys should be able to work without access to the keypair used when the release was built.

### Archive
The buffer is tarred and saved as a file with the release hash as the filename.

### Build
The buffer is searched for any docker base images and they are built first. For every node in the buffer, its docker image is built with a repository/tag of `system_name/node_type#release_hash`.

### Push
All docker base images and node images are pushed to the private registry.

### Run build plugins
All described build plugins are executed. Each plugin has access to the buffer.


## Deploy

The `deploy` step pulls the archived release, runs deploy plugins, parses and generates node configurations, and pushes images and configurations to the nodes.

The stages of the deploy step:

  1. Pull release
  2. Run pre-deploy plugins
  3. Pull compiled node configuration
  4. Push images and configurations to nodes
  5. Run post-deploy plugins

This deploy step is normally executed after a build, but it is also run when a release is applied to an environment in either a deploy or rollback.

When an environment is changed (structure, services, hosts), this deploy step is partially executed. Since configuration alone needs to be updated across nodes, plugins and image pushing (stages 1, 2, parts of stage 4, and 5) are skipped because they are unnecessary.

### Pull release
The release to be deployed is selected from the archives and extracted into the buffer. The release to be deployed is extracted and the existing release is temporarily kept so that the deploy plugins can access them. For example, during the deploy step, the migration plugin needs access to the files of both the old and new releases. During a standard deploy, the plugin migrates the database to the most recent migration in the new release. However, if the deploy is a rollback, only the newer release will contain the extra migration data needed to rollback. The plugin will find the most recent migration in the older release and will use the migrations in the newer release to rollback he database.

### Run pre-deploy plugins
Plugins and plugin configuration are loaded, and all pre-deploy plugins are executed according to their priority. Like sources, plugins defined later are executed after plugins defined earlier.

### Push images and configurations to nodes
The release's compiled node configuration file is loaded and parsed. The parsing yields a configuration tree for each nodes. These configuration trees are pushed to their corresponding nodes. Each node pulls their corresponding images from the docker registry.

### Run post-deploy plugins
Like the pre-deploy plugins, all post-deploy plugins are executed with access to both the old and new releases.
