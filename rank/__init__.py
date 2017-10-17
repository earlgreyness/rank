from functools import partial
import json

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from rank.utils import configure_logging


class SQLAlchemyCustomized(SQLAlchemy):
    def apply_driver_hacks(self, app, info, options):
        SQLAlchemy.apply_driver_hacks(self, app, info, options)
        # Option relevant only for psycopg2 driver.
        # See SQLAlchemy docs on PostgreSQL for reference.
        # It is passed as parameter to psycopg2's create_engine.
        options['json_serializer'] = partial(
            json.dumps, **app.config.get('POSTGRESQL_JSON', {}))


app = Flask(__name__)
app.config.from_object('rank.config')
configure_logging(app)
db = SQLAlchemyCustomized(app)

import rank.models
import rank.api
