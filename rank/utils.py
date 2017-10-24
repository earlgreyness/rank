import logging.config
import logging
from functools import wraps
from urllib.parse import urlparse


def configure_logging(app):
    # Triggers removing existing handlers when accessed first time:
    app.logger
    logging.config.dictConfig(app.config['LOGGING'])


def handle_exceptions(f):
    logger = logging.getLogger(__name__)

    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception:
            logger.exception('')

    return decorated


def domain(url):
    if not urlparse(url).scheme:
        url = 'http://' + url
    return urlparse(url).netloc
