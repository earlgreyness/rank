import logging.config


def configure_logging(app):
    # Triggers removing existing handlers when accessed first time:
    app.logger
    logging.config.dictConfig(app.config['LOGGING'])
