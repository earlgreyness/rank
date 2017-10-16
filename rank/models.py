from functools import partial

from sqlalchemy import Column as BaseColumn, Integer, String
from sqlalchemy_utils import ArrowType

from rank import db, app

Column = partial(BaseColumn, nullable=False)
