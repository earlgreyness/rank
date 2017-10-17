import os.path as op

from crontab import CronTab

from rank import app


def main():

    def script(name):
        root = op.normpath(op.join(app.config['PROJECT_ROOT'], '..'))
        py = op.join(root, 'venv', 'bin', 'python3')
        return '{} {}'.format(py, op.join(root, name))

    cron = CronTab(user=True)
    cron.remove_all()
    cron.new(script('do.py')).minute.every(1)
    cron.write(user=True)


if __name__ == '__main__':
    main()
