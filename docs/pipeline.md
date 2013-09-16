# Stretch Pipeline

The Stretch Pipeline moves apps and their configurations from sources to the backend. There are many stages in the pipeline, each allowing a degree of configuration and flexibility. Essentially, the pipeline consists of two major steps: `build` and `deploy`. The output for both of these steps are logged for realtime display in the web client. 


## Build

The `build` step builds a release by pulling apps and their configurations from sources, archiving the apps and configurations, running build plugins, building docker images for the apps, and pushing the newly-built images to the private registry.

The stages of the build step:

  1. Pull from sources
  2. Decrypt
  3. Compile configuration
  3. Archive
  4. Build docker images
  5. Push to registry
  6. Run build plugins

### Pull from sources

Code is pulled from all defined sources and placed in a temporary buffer folder. Sources overwrite each other based on source priority. Source priority is determined by the order of source declaration in the stretch configuration. Sources defined later override sources defined earlier.

### Decrypt

The buffer is checked for the release [Build Files](build_files.md). These files are parsed in order to find all secret configuration data and encrypted files which are then decrypted with the private key. Decrypted configuration data is inserted into the existing release Build Files with the use of the `encrypted` directive. The parsed data is also used by the following stage.

Decryption takes place before archiving because the private key is assumed to be ephemeral. Rollbacks and other deploys should be able to work without access to the keypair used when the release was built.

### Compile configuration

The parsed data from the previous stage is used to compile the *release configuration*. All global and node-based configuration is compiled into this one block of data, the *release configuration*, to accelerate configuration deploys. 

### Archive

The buffer is tarred and saved as a `.tar` file with the release hash as the filename. The *release configuration* is saved as a `.conf` file with the release hash as the filename.

### Build docker images

The buffer is searched for any docker base images and they are built first. For every node in the buffer, its docker image is built with a repository/tag of `system_name/node_type#release_hash`.

### Push to registry

All docker base images and node images are pushed to the private registry.

### Run build plugins

All described build plugins are executed. Each plugin has access to the buffer.


## Deploy

The `deploy` step pulls the archived release, runs deploy plugins, parses and generates node configurations, and pushes images and configurations to the nodes.

The stages of the deploy step:

  1. Pull release
  2. Run pre-deploy plugins
  3. Pull release configuration
  4. Push images and configurations to nodes
  5. Change release
  6. Switch buffers
  7. Run post-deploy plugins

This deploy step is normally executed after a build, but it is also run when a release is applied to an environment in either a deploy or rollback.

When an environment is changed (structure, services, hosts), this deploy step is partially executed. Since configuration alone needs to be updated across nodes, plugins and image pushing (stages 1, 2, parts of stage 4, and 5, 6, 7) are skipped because they are unnecessary. Instead of a completely changed release (stage 5), the nodes are just commanded to load new configuration.

Two release buffers are used in the deploy step: the *new release buffer* and the *existing release buffer*. Release buffers are basically folders that contain releases. They are solely used by plugins that inspect both the existing and new release on each deploy. Each environment has both of these release buffers. Since both buffers are stored on the file system, they persist even after deployment. This fully eliminates the need to pull both releases for every deploy, but if any of the buffers are nonexistent or corrupted, stretch will pull the correct releases, and will continue with deployment.

### Pull release

The release to be deployed is selected from the archives and extracted into the *new release buffer*. Both buffers are configured to be accessed by deploy plugins. For example, during the deploy step, the migration plugin needs access to the files of both the old and new releases. During a standard deploy, the plugin migrates the database to the most recent migration in the new release. However, if the deploy is a rollback, only the existing release will contain the extra migration data needed to rollback. This is because only the existing release contains the `down` migrations that the release being rolled back to doesn't have. The plugin will find the most recent migration in the new release and will use the migrations in the existing release to rollback the database.

### Run pre-deploy plugins

Plugins and plugin configuration are loaded, and all pre-deploy plugins are executed according to their priority. Plugins defined later in the stretch configuration files are executed after plugins defined earlier.

### Pull release configuration

The *release configuration* is loaded from the archives. Since the *release configuration* is a template, it is compiled and parsed to return a configuration tree for each node.

### Push images and configurations to nodes

The configuration trees are pushed to their corresponding nodes. Each node pulls their corresponding images from the docker registry.

### Change release

Each node affected by the deploy is then commanded via it's agent to switch to the new release. This process is done incrementally based on groups to prevent a full system outage and to ensure a zero-downtime deploy.

### Switch buffers

The release in the *existing release buffer* is replaced with the release in the *new release buffer*. The *new release buffer* is now empty.

### Run post-deploy plugins

Like the pre-deploy plugins, all post-deploy plugins are executed with access to both the existing and new releases.
