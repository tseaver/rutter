from pyramid.config import Configurator
from pyramid.view import view_config

@view_config(renderer='string')
def hello_alpha(request):
    return 'Hello, Alpha'

def main(global_config=None, **local_config):
    config = Configurator()
    config.scan()
    return config.make_wsgi_app()
