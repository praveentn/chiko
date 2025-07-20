# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate   # optional, but most people use it

db = SQLAlchemy()
migrate = Migrate()
