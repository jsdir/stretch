import os
import json
import tarfile
import datetime
import logging
from peewee import SqliteDatabase, Model, CharField, TextField, DateTimeField

from stretch.snapshot import Snapshot
from stretch.source import Source
from stretch import config, utils, sources

log = logging.getLogger(__name__)


class Release(Model):
    name = CharField()
    release_id = CharField(unique=True)
    containers = TextField()
    created_at = DateTimeField(default=datetime.datetime.now)


@utils.memoized
def get_db():
    print config.get_config()['database_path']
    db = SqliteDatabase(config.get_config()['database_path'])
    if not Release.table_exists():
        Release.create_table()


def get_archive_path(release_id):
    release_dir = os.path.join(config.get_config()['data_dir'], 'releases')
    return os.path.join(release_dir, '%s.tar.gz' % release_id)


def create_release(source_name, options, release_id):
    conf = config.get_config()
    db = get_db()

    # Check if a release with the same id exists.
    if release_id:
        if Release.select().where(Release.release_id == release_id).exists():
            raise KeyError('a release with the id "%s" already exists'
                           % release_id)

    # Pull, archive, and save the release.
    path, reference = Source.get(source_name).pull(options)
    release_id = release_id or reference or utils.generate_random_hex(16)

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
        containers = snapshot.build(release)

    log.info("Built containers: %s" % containers)
    # Persist the release
    release.containers = json.dumps(containers)
    release.save()

    return release_id
