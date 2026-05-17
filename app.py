import os
from flask import Flask
from flask_login import current_user
from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from dotenv import load_dotenv
from config import config
from extensions import db, login_manager, limiter

load_dotenv()

migrate = Migrate()
csrf = CSRFProtect()
login_manager.login_view = 'main.login'


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    if config_name == 'production' and not os.environ.get('SECRET_KEY'):
        raise ValueError("SECRET_KEY environment variable must be set in production")

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)

    from routes.main import main_bp
    app.register_blueprint(main_bp)

    from models import User, Group, Membership, Expense, ExpenseSplit

    @app.context_processor
    def inject_user_initials():
        if current_user.is_authenticated:
            fn = current_user.first_name or ''
            ln = current_user.last_name or ''
            if fn and ln:
                initials = (fn[0] + ln[0]).upper()
            elif current_user.email:
                initials = current_user.email[:2].upper()
            else:
                initials = '??'
            return dict(initials=initials)
        return dict(initials='--')

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
