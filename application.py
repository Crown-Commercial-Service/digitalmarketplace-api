import os

from flask_migrate import Migrate

from app import create_app, db


application = create_app(os.getenv("DM_ENVIRONMENT") or "development")
migrate = Migrate(application, db)
