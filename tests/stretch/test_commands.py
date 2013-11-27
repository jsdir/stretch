from mock import patch

from stretch import commands


'''
def test_run():
    #with patch('stretch.agent.run') as run:
    #    commands.run(['agent'])
    #    run.assert_called_with()

    with patch('django.core.management.call_command') as call_command:
        commands.run(['autoload'])
        call_command.assert_called_with('autoload')
        commands.run(['server'])
        call_command.assert_called_with('run_gunicorn')

        # Check default command
        call_command.clear_mock()
        commands.run([])
        call_command.assert_called_with('run_gunicorn')

    with patch('djcelery.management.commands.celery.Command.run_from_argv') as run_from_argv:
        commands.run(['celery'])
        run_from_argv.assert_called_with(['manage.py', 'celery', 'worker'])
'''
