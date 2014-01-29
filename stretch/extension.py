from stretch import config


class ExtensionException(Exception): pass


class Extension(object):

    def __init__(self, options):
        self.options = options

    @classmethod
    def get(cls, name):
        # Ensure configuration section exists.
        try:
            extensions = config.get_config()[cls.config_section]
        except KeyError:
            raise ExtensionException('no configuration section named '
                '"%s" in config.yml' % cls.config_section)

        for extension, data in extensions.iteritems():
            # Find matches by name.
            if name == extension:
                # Ensure extension has a defined type.
                try:
                    extension_type = data['type']
                except KeyError:
                    raise ExtensionException('"type" undefined for %s "%s"'
                                             % (cls.name, name))

                # Attempt to load the extension.
                for subclass in cls.__subclasses__():
                    if subclass.name == extension_type:
                        return subclass(data.get('options', {}))

        # Raise an exception if the extension was not found.
        raise ExtensionException('could not find %s "%s" in config.yml'
                                 % (cls.name, name))


    def get_option(self, name):
        """
        Returns the option with `name` and returns None if not found.

        :Parameters:
          - `name`: the option's name
        """
        return self.options.get(name, None)

    def require_option(self, name):
        """
        Returns the option with `name` and fails if not found.

        :Parameters:
          - `name`: the option's name
        """
        option = self.options.get(name, None)
        if not option:
            raise NameError('no option "%s" defined' % name)
        return option
