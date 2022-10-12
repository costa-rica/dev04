from flask import Flask
from wsh_config import ConfigDev, ConfigProd
import logging
from logging.handlers import RotatingFileHandler
import os

config_object = ConfigDev()

logs_dir = os.path.join(os.getcwd(), 'logs')

if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

#Setting up Logger
formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
formatter_terminal = logging.Formatter('%(asctime)s:%(filename)s:%(name)s:%(message)s')

logger_init = logging.getLogger('__init__')
logger_init.setLevel(logging.DEBUG)

file_handler = RotatingFileHandler(os.path.join(logs_dir,'__init__.log'), mode='a', maxBytes=5*1024*1024,backupCount=2)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter_terminal)

logger_init.addHandler(file_handler)
logger_init.addHandler(stream_handler)

#set werkzeug handler
logging.getLogger('werkzeug').setLevel(logging.DEBUG)
logging.getLogger('werkzeug').addHandler(file_handler)
#End set up logger

logger_init.info(f'--- Starting wsh07 API ---')





def create_app():
    app = Flask(__name__)
    app.config.from_object(config_object)
    # print('**', dir(app.config))
    # print('**', app.config.keys())
    # print('**', app.config.get('ENV'))
    logger_init.info(f"--- Running ENV: {app.config.get('ENV')}")

    from app_package.scheduler.routes import sched_route
    # from app_package.dashboard.routes import dash
    
    app.register_blueprint(sched_route)
    # app.register_blueprint(dash)
    
    return app      
