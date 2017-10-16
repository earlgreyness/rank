from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from rank.utils import configure_logging

app = Flask(__name__)
app.config.from_object('rank.config')
configure_logging(app)
db = SQLAlchemy(app)

import rank.models
import rank.api
