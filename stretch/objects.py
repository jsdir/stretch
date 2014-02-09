import os
import json
import tarfile
import datetime
import logging
from ago import human
from peewee import SqliteDatabase, Model, CharField, TextField, DateTimeField

from stretch.snapshot import Snapshot
from stretch.source import Source
from stretch import config, utils, sources

log = logging.getLogger(__name__)
db = SqliteDatabase(None)


class Release(Model):
    name = CharField()
    release_id = CharField(unique=True)
    containers = TextField()
    created_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = db


def get_archive_path(release_id):
    release_dir = os.path.join(config.get_config()['data_dir'], 'releases')
    return os.path.join(release_dir, '%s.tar.gz' % release_id)


def check_release(release_id):
    if Release.select().where(Release.release_id == release_id).exists():
        raise KeyError('a release with the id "%s" already exists'
                       % release_id)


def create_release(source_name, options, release_id):
    log.info('Creating release...')

    conf = config.get_config()

    # Check if a release with the same id exists.
    if release_id:
        check_release(release_id)

    # Pull, archive, and save the release.
    path, reference = Source.get(source_name).pull(options)

    if not release_id:
        release_id = reference or utils.generate_random_hex(16)
        check_release(release_id)

    # Check if a release with the same id exists.
    if release_id:
        if Release.select().where(Release.release_id == release_id).exists():
            raise KeyError('a release with the id "%s" already exists'
                           % release_id)

    # Archive the release
    release_dir = os.path.join(conf['data_dir'], 'releases')
    utils.make_dir(release_dir)

    archive_path = get_archive_path(release_id)
    tar_file = tarfile.open(archive_path, 'w:gz')
    tar_file.add(path, '/')
    tar_file.close()

    # Prepare the release object
    release = Release(
        release_id=release_id,
        name=utils.generate_memorable_name()
    )

    # Build the release
    with Snapshot.create_from_archive(archive_path) as snapshot:
        # TODO: Reset timestamps until caching issue resolved.
        # https://github.com/dotcloud/docker/issues/3556
        log.info('Normalizing timestamps...')
        utils.run(cmd, shell=True)
        cmd = 'find %s -exec touch -t 200001010000.00 {} ";"' % snapshot.path

        containers = snapshot.build(release)

    log.info("Built containers: %s" % json.dumps(containers, indent=4))

    # Persist the release
    release.containers = json.dumps(containers)
    release.save()

    return release_id


def deploy(release, env_path):
    log.info('Deploying release "%s"...' % release)

    # Get environment
    env = EtcdNode(env_path)

    # Get the release
    try:
        release = Release.select().where(
            (Release.release_id == release) or
            (Release.release_name == release)
        ).get()
    except Release.DoesNotExist:
        raise NameError('a release with the identifier "%s" could not be '
            'found. See `stretch ls --releases`.' % release)

    containers = json.loads(release.containers)
    log.info("Found release containers: %s" % json.dumps(containers, indent=4))

    archive_path = get_archive_path(release.release_id)
    with Snapshot.create_from_archive(archive_path) as snapshot:
        snapshot.run_task('before_deploy', release)
        deploy_to_environment(containers, env)
        snapshot.run_task('after_deploy', release)


class EtcdNode(object):
    def __init__(self, path):
        self.path = path


class Host(EtcdNode):
    @property
    def agent(self):
        return AgentClient(self.getSubKey())


def deploy_to_environment(containers, env):
    # use twisted batch
    pushed_containers = []
    for group in env.get('groups'):
        image = containers.get(group.node)
        if image:
            for host in group:
                container_tag = '%s/%s/%s:%s' % (
                    settings.registry,
                    settings.registry_namespace,
                    group.node,
                    release_id
                )

                # Push container to registry if not done already.
                if container_tag not in pushed_containers:
                    pushed_containers.append(container_tag)
                    docker.tag(image, container_tag)
                    docker.push(container_tag)

                agent = Host(path).agent
                agent.pull(container_tag).then(batch_size)
                agent.deploy(container_tag, system=system, env=env, group=group)


def list_releases():
    print '- releases:'
    release_found = False
    for release in Release.select().limit(30):
        release_found = True
        print '  - %s [%s] (created %s)' % (release.name, release.release_id,
                                            human(release.created_at, precision=1))

    if not release_found:
        print "No releases created yet."
