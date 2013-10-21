from wsgiref.simple_server import make_server

from rutter.urlmap import URLMap

from alpha import main as alpha_main
from bravo import main as bravo_main

def main():
    # Grab the config, add a view, and make a WSGI app
    urlmap = URLMap()
    urlmap['/alpha'] = alpha_main()
    urlmap['/bravo'] = bravo_main()
    return urlmap

if __name__ == '__main__':
    # When run from command line, launch a WSGI server and app
    app = main()
    server = make_server('0.0.0.0', 6543, app)
    server.serve_forever()
