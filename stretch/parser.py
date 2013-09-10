import os
import yaml
import collections


def update(d, u):
    """
    Recursively merge dict-like objects
    """
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            r = update(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


def get_nodes(path):
    result = {'plugins': {}, 'nodes': {}}

    data = get_node(path)
    if data:
        nodes = data.get('nodes')
        if nodes:
            # file is root descriptor

            # global configuration
            config = data.get('config') or {}

            # local options
            local_options = {}
            local_data = data.get('local_options')
            if local_data:
                for options in local_data.values():
                    if options.has_key('includes'):
                        includes = options.pop('includes')
                        for node_name in includes:
                            if local_options.has_key(node_name):
                                update(local_options[node_name], options)
                            else:
                                local_options[node_name] = options

            # plugins
            plugins = data.get('plugins')
            if plugins:
                result['plugins'] = plugins

            for node_name, node_path in nodes.iteritems():
                full_node_path = os.path.join(path, node_path)

                # apply global configuration
                node_data = {'config': dict(config)}

                # apply local options
                node_local_data = local_options.get(node_name)
                if node_local_data:
                    update(node_data, node_local_data)

                # apply file options
                update(node_data, get_node(full_node_path))

                result['nodes'][node_name] = node_data
        else:
            # file is node descriptor
            node_data = get_node(path)
            node_name = node_data.get('node')
            if node_name:
                result['nodes'][node_name] = node_data
            else:
                # no node name error
                pass

    return result


def get_node(path):
    stretch_file = os.path.join(path, 'stretch.yml')
    data = {}

    if os.path.exists(stretch_file):
        with open(stretch_file) as source:
            data = yaml.load(source.read())

    return data
