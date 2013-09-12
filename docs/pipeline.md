# Stretch Pipeline

The stretch pipeline moves apps and their configurations from sources to the backend. There are many stages in the pipeline, each allowing a degree of configuration and flexibility. Essentially, the pipeline consists of two major steps: `build` and `deploy`.


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
The current sources are pulled from

### Decrypt
The buffer is processed and decrypted according to the private key. Decryption takes place before archiving because the private key is assumed to be ephemeral.

### Archive
Things are tarred.

### Build
`docker build -t <system>/<node>#<ref>`

### Push
`docker push <system>/<node>#<ref>  // to private registry`

### Run build plugins
nothing


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
For the plugins

### Run pre-deploy plugins
none

### Pull compiled node configuration

  1. Pull release node configuration
  2. Parse/Generate node configurations
  3. Push configurations to nodes

Stretch can pull configuration from both services and sources.

### Push images and configurations to nodes
none

### Run post-deploy plugins
none
