# import ...


class PluginEnvironment(object):
    def __init__(self, version):
        self.version = version

    def install(self):
        raise NotImplementedError


class PythonPluginEnvironment(PluginEnvironment):
    def __init__(self):
        pass
    #     super(PythonPluginEnvironment, self).__init__()
    #     self.version = version
    def install(self):
        os.run('install virtualenv')
        os.run('install python-pip in virtualenv')

    def install_package(self, package, version):
        os.run('pip install %s==%s' % (package, version))


class NodePluginEnvironment(PluginEnvironment):
    def install(self):
        os.run('install npm')
        os.run('')

    def is_installed(self):
        pass # return os.run('npm, node')

    # def __init__(self, version):
    #     super(NodePluginEnvironment, self).__init__()
    #     self.version = version


class Plugin(object):
    def __init__(self):
        pass

    def before_release_change(self, old_release, new_release, env):
        pass # TODO: log before release change trigger

    def after_release_change(self, old_release, new_release, env):
        pass # TODO: log before release change trigger


class MigrationsPlugin(Plugin):
    def __init__(self):
        super(MigrationsPlugin, self).__init__()
        self.name = 'migrations'
        self.plugin_environment = NodePluginEnvironment('0.10.17')
        # ^ Whatever node version

    def before_release_change(self, old_release, new_release, env):
        # Migrations are done before releases are rolled out.
        # TODO: super before_release_change for logging
        # TODO: release comparison....
        pass


class GruntPlugin(Plugin):
    def __init__(self):
        super(GruntPlugin, self).__init__()
        self.name = 'grunt'
        self.plugin_environment = NodePluginEnvironment('0.10.17')
