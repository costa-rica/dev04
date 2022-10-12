from flask import Flask
from wsh_config import ConfigDev, ConfigProd
from wsh_models import login_manager
from flask_mail import Mail
import os


if os.environ.get('COMPUTERNAME')=='CAPTAIN2020' or os.environ.get('COMPUTERNAME')=='NICKSURFACEPRO4':
    config_object = ConfigDev()
    print('* ---> Configured for Development')
else:
    config_object = ConfigProd()
    print('* ---> Configured for Production')
    

mail = Mail()
def create_app():
    app = Flask(__name__)
    app.config.from_object(config_object)
    # print('app.config.get("ENV") says it is ---> ', app.config.get('ENV'))

    login_manager.init_app(app)
    mail.init_app(app)

    from app_package.users.routes import users
    from app_package.dashboard.routes import dash
    from app_package.errors.routes import errors
    
    app.register_blueprint(users)
    app.register_blueprint(dash)
    app.register_blueprint(errors)
    
    return app      
