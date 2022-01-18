""" Map URL prefixes to WSGI applications.  See ``URLMap``

Forked from ``paste.urllib``.
"""
try:
    from collections.abc import MutableMapping
except ImportError:  # pragma: NO COVER Python2
    from collections import MutableMapping
try:
    from html import escape
except ImportError:  # pragma: NO COVER Python2
    from cgi import escape
import re

from webob.exc import HTTPNotFound

def _parse_path_expression(path):
    """ Parse a path expression for a path alone.
    
    E.g., for 'domain foobar.com port 20 /', return '/'; for '/foobar'
    return '/foobar'
    
    Return as an address that URLMap likes.
    """
    parts = path.split()
    domain = port = path = None
    while parts:
        if parts[0] == 'domain':
            parts.pop(0)
            if not parts:
                raise ValueError("'domain' must be followed with a domain name")
            if domain:
                raise ValueError("'domain' given twice")
            domain = parts.pop(0)
        elif parts[0] == 'port':
            parts.pop(0)
            if not parts:
                raise ValueError("'port' must be followed with a port number")
            if port:
                raise ValueError("'port' given twice")
            port = parts.pop(0)
        else:
            if path:
                raise ValueError("more than one path given (have %r, got %r)"
                                 % (path, parts[0]))
            path = parts.pop(0)
    s = ''
    if domain:
        s = 'http://%s' % domain
    if port:
        if not domain:
            raise ValueError("If you give a port, you must also give a domain")
        s += ':' + port
    if path:
        if s and not path.startswith('/'):
            s += '/'
        s += path
    return s


_NORM_URL_RE = re.compile('//+')
_DOMAIN_URL_RE = re.compile('^(http|https)://')

def _default_not_found_app(environ, start_response):
    mapper = environ.get('paste.urlmap_object')
    if mapper:
        matches = [p for p, a in mapper.applications]
        extra = 'defined apps: %s' % (
            ',\n  '.join(map(repr, matches)))
    else:
        extra = ''
    extra += '\nSCRIPT_NAME: %r' % environ.get('SCRIPT_NAME')
    extra += '\nPATH_INFO: %r' % environ.get('PATH_INFO')
    extra += '\nHTTP_HOST: %r' % environ.get('HTTP_HOST')
    # XXX WebOb?
    exc = HTTPNotFound(environ['PATH_INFO'], comment=escape(extra, quote=False))
    return exc(environ, start_response)

def _normalize_url(url, trim=True):
    """Return ``(domain, path)`` tuple for ``url``.

    If ``trim`` is True, remove any trailing slash from ``path``.
    """
    if isinstance(url, (list, tuple)):
        domain = url[0]
        url = _normalize_url(url[1])[1]
        return domain, url
    if not (not url or url.startswith('/')
            or _DOMAIN_URL_RE.search(url)):
        raise ValueError(
            "URL fragments must start with / or http:// (you gave %r)"
            % url)
    match = _DOMAIN_URL_RE.search(url)
    if match:
        url = url[match.end():]
        if '/' in url:
            domain, url = url.split('/', 1)
            url = '/' + url
        else:
            domain, url = url, ''
    else:
        domain = None
    url = _NORM_URL_RE.sub('/', url)
    if trim:
        url = url.rstrip('/')
    return domain, url


class URLMap(MutableMapping):
    """Dispatch to one of several applications based on the URL.

    The dictionary keys are URLs to match (like
    ``PATH_INFO.startswith(url)``), and the values are applications to
    dispatch to.  URLs are matched most-specific-first, i.e., longest
    URL first.  The ``SCRIPT_NAME`` and ``PATH_INFO`` environmental
    variables are adjusted to indicate the new context.

    URLs can also include domains, like ``http://blah.com/foo``, or as
    tuples ``('blah.com', '/foo')``.  This will match domain names; without
    the ``http://domain`` or with a domain of ``None`` any domain will be
    matched (so long as no other explicit domain matches).
    """
    def __init__(self, not_found_app=_default_not_found_app):
        self.applications = []
        self.not_found_application = not_found_app

    def _sort_apps(self):
        """Sort applications, longest URLs first.

        Apps w/o domains sort *last*.
        """
        def key(app_desc):
            dom_url, app = app_desc
            domain, url = dom_url
            return domain or '\xff', -len(url)
        self.applications = sorted(self.applications, key=key)

    def __getitem__(self, url):
        dom_url = _normalize_url(url)
        for app_url, app in self.applications:
            if app_url == dom_url:
                return app
        raise KeyError(
            "No application with the url %r (domain: %r; existing: %s)"
            % (url[1], url[0] or '*', self.applications))

    def __setitem__(self, url, app):
        if app is None:
            try:
                del self[url]
            except KeyError:
                pass
            return
        dom_url = _normalize_url(url)
        if dom_url in self:
            del self[dom_url]
        self.applications.append((dom_url, app))
        self._sort_apps()

    def __delitem__(self, url):
        url = _normalize_url(url)
        for app_url, app in self.applications:
            if app_url == url:
                self.applications.remove((app_url, app))
                break
        else:
            raise KeyError(
                "No application with the url %r" % (url,))

    def keys(self):
        return [app_url for app_url, app in self.applications]

    def __iter__(self):
        return (x[0] for x in self.applications)

    def __len__(self):
        return len(self.applications)

    def __call__(self, environ, start_response):
        host = environ.get('HTTP_HOST', environ.get('SERVER_NAME')).lower()
        if ':' in host:
            host, port = host.split(':', 1)
        else:
            if environ['wsgi.url_scheme'] == 'http':
                port = '80'
            else:
                port = '443'
        hostport = host + ':' + port
        path_info = environ.get('PATH_INFO')
        path_info = _normalize_url(path_info, False)[1]
        for dom_url, app in self.applications:
            domain, app_url = dom_url
            if domain and domain != host and domain != hostport:
                continue
            if (path_info == app_url
                or path_info.startswith(app_url + '/')):
                environ['SCRIPT_NAME'] += app_url
                environ['PATH_INFO'] = path_info[len(app_url):]
                return app(environ, start_response)
        environ['paste.urlmap_object'] = self
        return self.not_found_application(environ, start_response)

def urlmap_factory(loader, global_conf, **local_conf):
    if 'not_found_app' in local_conf:
        not_found_app = local_conf.pop('not_found_app')
    else:
        not_found_app = global_conf.get('not_found_app')
    if not_found_app:
        not_found_app = loader.get_app(not_found_app, global_conf=global_conf)
    if not_found_app is not None:
        urlmap = URLMap(not_found_app=not_found_app)
    else:
        urlmap = URLMap()
    for path, app_name in local_conf.items():
        path = _parse_path_expression(path)
        app = loader.get_app(app_name, global_conf=global_conf)
        urlmap[path] = app
    return urlmap
