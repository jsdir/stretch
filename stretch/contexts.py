def plugin_context(deploy):
    return {
        'config': deploy.environment.config,
        'environment': deploy.environment.name,
        'release': deploy.release.name,
        'release_sha': deploy.release.sha,
        'existing_release': deploy.existing_release.name,
        'existing_release_sha': deploy.existing_release.sha
    }
