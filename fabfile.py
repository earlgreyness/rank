import os.path as op
import importlib
import sys
from urllib.parse import urlparse

from fabric.api import put, settings, run, env, local, get
from fabric.context_managers import cd, lcd
from fabric.contrib import files

PROJ = 'rank'
HOST = '188.227.72.189'
FILES = [
    PROJ + '_uwsgi.py',
    PROJ + '_uwsgi.ini',
    'requirements.txt',
    'setup_cron.py',
    'do.py',
]

LOCAL_ROOT = op.dirname(op.realpath(__file__))
sys.path.insert(0, op.join(LOCAL_ROOT, PROJ))
# Importing config as a standalone file, not within PROJ module:
config = importlib.import_module('config')
REMOTE_ROOT = '/home/{}/back'.format(PROJ)
NGINX = PROJ + '.nginx'
SYSTEMD = PROJ + '_uwsgi.service'

env.hosts = [HOST]
env.user = PROJ
env.shell = '/bin/bash -c'  # dropped -l flag
env.colorize_errors = True


def psql(command):
    command = 'psql -c "{}"'.format(command)
    sent = 'sudo -u postgres {}'.format(command)
    with settings(user='root'):
        run(sent)


def _create_user(username, password):
    psql('''CREATE USER "{username}" WITH PASSWORD '{password}';'''.format(**locals()))


def _create_database(dbname, username):
    psql(
        '''CREATE DATABASE "{dbname}" WITH encoding='utf8'
               template="template0"
               LC_COLLATE='ru_RU.UTF-8'
               LC_CTYPE='ru_RU.UTF-8';'''.format(**locals()))
    psql('''GRANT ALL PRIVILEGES ON DATABASE "{dbname}" to "{username}";'''.format(**locals()))


def setup_nginx():
    with settings(user='root'), lcd(LOCAL_ROOT):
        put(NGINX, '/etc/nginx/sites-available/')
        run('ln -s -f /etc/nginx/sites-available/{} /etc/nginx/sites-enabled/'.format(NGINX))
        run('nginx -t')
        run('systemctl reload nginx')


def setup_db():
    db = urlparse(config.SQLALCHEMY_DATABASE_URI)
    dbname = db.path.lstrip('/')
    _create_user(db.username, db.password)
    _create_database(dbname, db.username)


def setup_systemd():
    with settings(user='root'), lcd(LOCAL_ROOT):
        put(SYSTEMD, '/etc/systemd/system/')
        run('systemctl enable {}'.format(SYSTEMD))
        run('systemctl start {}'.format(SYSTEMD))


def reload():
    with settings(user='root'):
        run('systemctl restart {}'.format(SYSTEMD))


def deploy(full=False, db=False):
    if db:
        setup_db()
    run('mkdir -p {}'.format(REMOTE_ROOT))

    with cd(REMOTE_ROOT), lcd(LOCAL_ROOT):
        run('mkdir -p logs')

        for filename in FILES:
            put(filename, '.')

        local('find . -type d -name __pycache__ -prune -exec rm -R -f {} \;')
        run('rm -R -f {}'.format(PROJ))
        put(PROJ, '.')

        if not files.exists('venv'):
            run('python3 -m venv venv')

        run('venv/bin/pip3 install --upgrade pip')
        run('venv/bin/pip3 install -r requirements.txt')

        if 'setup_cron.py' in FILES:
            run('venv/bin/python3 setup_cron.py')

    if full:
        setup_systemd()
        setup_nginx()
    reload()


def download(page_id):
    with cd(REMOTE_ROOT), lcd(LOCAL_ROOT):
        cmd = 'from rank.models import Page; t = Page.query.get({}).get_text(); print(t)'.format(page_id)
        run('venv/bin/python3 -c "{}" > html.html'.format(cmd))
        get('html.html', '.')
        run('rm html.html')
