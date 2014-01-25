from django.db import models
from twisted.internet import defer, threads
from celery.utils.log import get_task_logger
from crochet import setup, wait_for_reactor
from django.conf import settings

from stretch.models import AuditedModel
from stretch import utils


log = get_task_logger(__name__)
setup()


class Deploy(AuditedModel):

    class Meta:
        app_label = 'stretch'

    environment = models.ForeignKey('Environment', related_name='deploys')
    task_id = models.CharField(max_length=128, unique=True)
    release = models.ForeignKey('Release', related_name='deploys_to')
    existing_release = models.ForeignKey(
        'Release', related_name='deploys_from', null=True
    )

    @classmethod
    def create(cls, env, release, task):
        deploy = cls(
            environment=env,
            task_id=task.request.id,
            release=release,
            existing_release=env.release
        )
        deploy.save()
        return deploy

    def run(self):
        # Build and push all images in the release
        with self.release.get_snapshot() as snapshot:
            snapshot.run_task('before_deploy', self.release)
            snapshot.build(self.release, self.environment.node_map)
            snapshot.run_task('after_deploy', self.release)

        # Deploy to instances
        env = self.environment
        env_path = '%s/%s' % (env.system.name, env.name)
        log.info('Deploying release[id:%s, tag:%s] to "%s"...' % (
            self.release.pk, self.release.tag, env_path
        ))

        self._deploy_to_instances()

        log.info('Successfully deployed to "%s".' % env_path)

    @wait_for_reactor
    def _deploy_to_instances(self):
        """
        Pulls all associated nodes for every host in the environment. After the
        nodes are pulled, all associated instances are restarted. Since this
        task would consume too much time to perform sequentially, and since
        most of the subtasks involved are largely IO-bound, twisted is used
        to handle these sets of tasks.

        A host has to pull nodes before its instances can restart and use the
        updated node. In order to follow this constraint while retaining
        concurrency, host and instance pools are used. Execution is blocked
        until both of these pools become empty.

        Batch size is used as a form of rate limiting to prevent excessive
        load on the image registry. The batch size is the maximum number of
        hosts that can download images from the registry at the same time.
        When a host is finished, another host is added to the pool. This
        continues until all hosts have pulled their images. When a host is
        finished pulling its images and templates, all of its instances are
        added to an instance pool.

        An instance pool is given to every group in the environment. The
        concurrency of each pool is determined by the number of instances it
        contains.
        """

        # Pull the release on all hosts
        all_tasks_finished = defer.Deferred()
        state = {'pull_tasks_finished': False, 'count': 0}
        groups = {}

        def on_restart_task_finished(result):
            state['count'] -= 1
            if state['pull_tasks_finished'] and state['count'] == 0:
                all_tasks_finished.callback(None)

        def on_pull_tasks_finished(result):
            state['pull_tasks_finished'] = True
            if state['count'] == 0:
                all_tasks_finished.callback(None)

        def pull_nodes(host):
            log.info('Pulling nodes on Host[%s]' % host.pk)
            deferred = host.agent.pull_nodes()

            def on_pull_task_finished(result):
                log.info('Finished pulling nodes on Host[%s]' % host.pk)
                state['count'] += 1
                host.restart_instances(groups).addBoth(
                    on_restart_task_finished
                )

            deferred.addBoth(on_pull_task_finished)
            return deferred

        pull_tasks = utils.deferred_batch_map(
            self.environment.hosts.all(), pull_nodes,
            settings.STRETCH_DEPLOY_BATCH_SIZE
        )

        pull_tasks.addBoth(on_pull_tasks_finished)

        return defer.DeferredList([pull_tasks, all_tasks_finished])
