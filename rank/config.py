import os.path as op

# flask-sqlalchemy
SQLALCHEMY_DATABASE_URI = 'postgresql://rank:b10D1KP604qA@localhost:5432/rank'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# flask-restful
RESTFUL_JSON = dict(ensure_ascii=False, sort_keys=True, indent=4)

# flask-cors
CORS_HEADERS = 'Content-Type'

# custom
CYCLE = 45 * 60  # sec
AMOUNT = 5
MIN_DELAY = 10 * 60  # sec
POSTGRESQL_JSON = dict(ensure_ascii=False, sort_keys=True, indent=2)
PROJECT_ROOT = op.dirname(op.realpath(__file__))
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] [%(levelname).1s] (%(module)s:%(lineno)d) %(message)s',
        },
    },
    'handlers': {
        'rotated': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': op.normpath(op.join(PROJECT_ROOT, '..', 'logs', 'app.log')),
            'maxBytes': 5 * 1024000,
            'backupCount': 3,
            'encoding': 'utf-8',
            'formatter': 'default',
            'level': 'DEBUG',
        },
    },
    'loggers': {
        'rank': {
            'level': 'DEBUG',
            'handlers': ['rotated'],
        },
    },
}
