# Build Files

The build files are a collection of stretch-specific files for every release. Together, they allow much of the environment infrastructure to be managed in version control. Deploys and rollbacks are made much more declarative. 

### Why not use services for everything?
Services are useful for configuration that is independent of the system's development cycle. Because services have no versions, environment rollbacks will have no effect on them. A service for an external database solution may change a port, address, or API key during the development cycle. When a rollback is issued, the service should continue to use the same current port, address, and API key instead of the now-defunct credentials existent at the time of that release. Services should not revert to their state during a previous release. These are the scenarios for which services were created.


