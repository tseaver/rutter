import unittest
from webtest import TestApp


class Test__parse_path_expression(unittest.TestCase):

    def _callFUT(self, path):
        from ..urlmap import _parse_path_expression
        return _parse_path_expression(path)

    def test_w_domain_empty(self):
        self.assertRaises(ValueError,
                          self._callFUT, 'domain')

    def test_w_domain_port_empty(self):
        self.assertRaises(ValueError,
                          self._callFUT, 'domain example.com port')

    def test_w_domain_duplicate(self):
        self.assertRaises(ValueError,
                          self._callFUT,
                          'domain example.com domain another.com')

    def test_w_port_only(self):
        self.assertRaises(ValueError,
                          self._callFUT, 'port 80')

    def test_w_port_duplicate(self):
        self.assertRaises(ValueError,
                          self._callFUT,
                          'domain example.com port 80 port 81')

    def test_w_path_duplicate(self):
        self.assertRaises(ValueError,
                          self._callFUT, '/foo /bar')

    def test_wo_domain_or_port(self):
        self.assertEqual(self._callFUT('/foo/bar'), '/foo/bar')

    def test_wo_domain_no_port(self):
        self.assertEqual(self._callFUT('domain example.com /foo/bar'),
                         'http://example.com/foo/bar')

    def test_wo_domain_and_port(self):
        self.assertEqual(self._callFUT('domain example.com port 81 /foo/bar'),
                         'http://example.com:81/foo/bar')

    def test_wo_domain_and_port_no_leading_slash(self):
        self.assertEqual(self._callFUT('domain example.com port 81 foo/bar'),
                         'http://example.com:81/foo/bar')


class Test__normalize_url(unittest.TestCase):

    def _callFUT(self, path, trim=None):
        from ..urlmap import _normalize_url
        if trim is None:
            return _normalize_url(path)
        return _normalize_url(path, trim)

    def test_w_tuple(self):
        domain, path = self._callFUT(('example.com', '/foo'))
        self.assertEqual(domain, 'example.com')
        self.assertEqual(path, '/foo')

    def test_w_list(self):
        domain, path = self._callFUT(['example.com', '/foo'])
        self.assertEqual(domain, 'example.com')
        self.assertEqual(path, '/foo')

    def test_w_string_w_http_domain(self):
        domain, path = self._callFUT('http://example.com/')
        self.assertEqual(domain, 'example.com')
        self.assertEqual(path, '')

    def test_w_string_w_https_domain(self):
        domain, path = self._callFUT('https://example.com/')
        self.assertEqual(domain, 'example.com')
        self.assertEqual(path, '')

    def test_w_string_wo_path(self):
        domain, path = self._callFUT('http://example.com')
        self.assertEqual(domain, 'example.com')
        self.assertEqual(path, '')

    def test_w_empty_string(self):
        domain, path = self._callFUT('')
        self.assertEqual(domain, None)
        self.assertEqual(path, '')

    def test_w_empty_path_w_trim(self):
        domain, path = self._callFUT('/')
        self.assertEqual(domain, None)
        self.assertEqual(path, '')

    def test_w_empty_path_wo_trim(self):
        domain, path = self._callFUT('/', trim=False)
        self.assertEqual(domain, None)
        self.assertEqual(path, '/')

    def test_w_non_slash_path(self):
        self.assertRaises(ValueError, self._callFUT, 'foo')

    def test_w_non_empty_path_w_trim(self):
        domain, path = self._callFUT('/foo/')
        self.assertEqual(domain, None)
        self.assertEqual(path, '/foo')

    def test_w_non_empty_path_wo_trim(self):
        domain, path = self._callFUT('/foo/', trim=False)
        self.assertEqual(domain, None)
        self.assertEqual(path, '/foo/')


class Test__default_not_found_app(unittest.TestCase):

    def _callFUT(self, environ, start_response):
        from ..urlmap import _default_not_found_app
        return _default_not_found_app(environ, start_response)

    def test_wo_mapper(self):
        environ = _makeEnviron()
        _started = []
        def _start_response(status, headers):
            _started.append((status, headers))
        result = list(self._callFUT(environ, _start_response))
        self.assertEqual(len(result), 1)
        lines = result[0].splitlines()
        self.assertEqual(lines[0], b'404 Not Found')
        self.assertEqual(lines[1], b'')
        self.assertEqual(lines[2], b'The resource could not be found.')
        self.assertEqual(lines[3], b'')
        self.assertEqual(lines[4], b" /  " +
                                   b" SCRIPT_NAME: ''" +
                                   b" PATH_INFO: '/'" +
                                   b" HTTP_HOST: 'example.com'  ")

    def test_w_mapper(self):
        _FOO, _BAR = object(), object()
        class _Mapper(object):
            applications = [('/foo', _FOO), ('/bar', _BAR)]
        environ = _makeEnviron()
        environ['paste.urlmap_object'] = _Mapper()
        _started = []
        def _start_response(status, headers):
            _started.append((status, headers))
        result = list(self._callFUT(environ, _start_response))
        self.assertEqual(len(result), 1)
        lines = result[0].splitlines()
        self.assertEqual(lines[0], b'404 Not Found')
        self.assertEqual(lines[1], b'')
        self.assertEqual(lines[2], b'The resource could not be found.')
        self.assertEqual(lines[3], b'')
        self.assertEqual(lines[4], b" / " +
                                   b" defined apps: '/foo',   '/bar'" +
                                   b" SCRIPT_NAME: ''" +
                                   b" PATH_INFO: '/'" +
                                   b" HTTP_HOST: 'example.com'  ")


class URLMapTests(unittest.TestCase):

    def _getTargetClass(self):
        from ..urlmap import URLMap
        return URLMap

    def _makeOne(self, not_found_app=None):
        if not_found_app is None:
            return self._getTargetClass()()
        return self._getTargetClass()(not_found_app)

    def test_ctor_wo_not_found_app(self):
        from ..urlmap import _default_not_found_app
        mapper = self._makeOne()
        self.assertEqual(mapper.applications, [])
        self.assertTrue(mapper.not_found_application is _default_not_found_app)

    def test_ctor_w_not_found_app(self):
        _NOT_FOUND = object()
        mapper = self._makeOne(_NOT_FOUND)
        self.assertEqual(mapper.applications, [])
        self.assertTrue(mapper.not_found_application is _NOT_FOUND)

    def test__sort_apps_empty(self):
        mapper = self._makeOne()
        mapper._sort_apps()
        self.assertEqual(mapper.applications, [])

    def test__sort_apps_non_empty(self):
        _APP1, _APP2, _APP3 = object(), object(), object()
        mapper = self._makeOne()
        mapper.applications.append(((None, '/foo'), _APP1))
        mapper.applications.append(((None, '/foo/bar'), _APP2))
        mapper.applications.append(((None, '/foobar'), _APP3))
        mapper._sort_apps()
        self.assertEqual(mapper.applications,
                         [((None, '/foo/bar'), _APP2),
                          ((None, '/foobar'), _APP3),
                          ((None, '/foo'), _APP1),
                         ])

    def test__sort_apps_non_empty_w_domains(self):
        _APP1, _APP2, _APP3, _APP4 = object(), object(), object(), object()
        mapper = self._makeOne()
        mapper.applications.append(((None, '/foo'), _APP1))
        mapper.applications.append(((None, '/foo/bar'), _APP2))
        mapper.applications.append(((None, '/foobar'), _APP3))
        mapper.applications.append((('example.com', '/foo'), _APP4))
        mapper._sort_apps()
        self.assertEqual(mapper.applications,
                         [(('example.com', '/foo'), _APP4),
                          ((None, '/foo/bar'), _APP2),
                          ((None, '/foobar'), _APP3),
                          ((None, '/foo'), _APP1),
                         ])

    def test___getitem___miss(self):
        mapper = self._makeOne()
        def _test():
            return mapper['/nonesuch']
        self.assertRaises(KeyError, _test)

    def test___getitem___hit(self):
        _APP1, _APP2 = object(), object()
        mapper = self._makeOne()
        mapper.applications.append(((None, '/foo/bar'), _APP2))
        mapper.applications.append(((None, '/foo'), _APP1))
        self.assertTrue(mapper['/foo'] is _APP1)
        self.assertTrue(mapper['/foo/bar'] is _APP2)

    def test___setitem___w_app_None_miss(self):
        mapper = self._makeOne()
        mapper[(None, '/nonesuch')] = None # no raise
        self.assertEqual(mapper.applications, [])

    def test___setitem___w_app_None_hit(self):
        _APP1 = object()
        mapper = self._makeOne()
        mapper.applications.append(((None, '/foo'), _APP1))
        mapper[(None, '/foo')] = None
        self.assertEqual(mapper.applications, [])

    def test___setitem___wo_existing(self):
        _APP1 = object()
        mapper = self._makeOne()
        mapper['/foo'] = _APP1
        self.assertEqual(mapper.applications, [((None, '/foo'), _APP1)])

    def test___setitem___w_existing(self):
        _APP1, _APP2 = object(), object()
        mapper = self._makeOne()
        mapper.applications.append(((None, '/foo'), _APP1))
        mapper['/foo'] = _APP2
        self.assertEqual(mapper.applications, [((None, '/foo'), _APP2)])

    def test___setitem___sorts(self):
        _APP1, _APP2, _APP3, _APP4 = object(), object(), object(), object()
        mapper = self._makeOne()
        mapper['/foo'] = _APP1
        mapper['/foo/bar'] = _APP2
        mapper['/foobar'] = _APP3
        mapper['http://example.com/foo'] = _APP4
        self.assertEqual(mapper.applications,
                         [(('example.com', '/foo'), _APP4),
                          ((None, '/foo/bar'), _APP2),
                          ((None, '/foobar'), _APP3),
                          ((None, '/foo'), _APP1),
                         ])

    def test___delitem___miss(self):
        mapper = self._makeOne()
        def _test():
            del mapper['/nonesuch']
        self.assertRaises(KeyError, _test)

    def test___delitem___hit(self):
        _APP1, _APP2 = object(), object()
        mapper = self._makeOne()
        mapper.applications.append(((None, '/foo/bar'), _APP2))
        mapper.applications.append(((None, '/foo'), _APP1))
        del mapper['/foo']
        self.assertEqual(mapper.applications,
                         [((None, '/foo/bar'), _APP2),
                         ])

    def test_keys_empty(self):
        mapper = self._makeOne()
        self.assertEqual(mapper.keys(), [])

    def test_keys_non_empty(self):
        _APP1, _APP2, _APP3, _APP4 = object(), object(), object(), object()
        mapper = self._makeOne()
        mapper['/foo'] = _APP1
        mapper['/foo/bar'] = _APP2
        mapper['/foobar'] = _APP3
        mapper['http://example.com/foo'] = _APP4
        self.assertEqual(mapper.keys(),
                         [('example.com', '/foo'),
                          (None, '/foo/bar'),
                          (None, '/foobar'),
                          (None, '/foo'),
                         ])

    def test___iter___empty(self):
        mapper = self._makeOne()
        self.assertEqual(list(mapper), [])

    def test___iter___non_empty(self):
        _APP1, _APP2, _APP3, _APP4 = object(), object(), object(), object()
        mapper = self._makeOne()
        mapper['/foo'] = _APP1
        mapper['/foo/bar'] = _APP2
        mapper['/foobar'] = _APP3
        mapper['http://example.com/foo'] = _APP4
        self.assertEqual(list(mapper),
                         [('example.com', '/foo'),
                          (None, '/foo/bar'),
                          (None, '/foobar'),
                          (None, '/foo'),
                         ])

    def test___len___empty(self):
        mapper = self._makeOne()
        self.assertEqual(len(mapper), 0)

    def test___len___non_empty(self):
        _APP1, _APP2, _APP3, _APP4 = object(), object(), object(), object()
        mapper = self._makeOne()
        mapper['/foo'] = _APP1
        mapper['/foo/bar'] = _APP2
        mapper['/foobar'] = _APP3
        mapper['http://example.com/foo'] = _APP4
        self.assertEqual(len(mapper), 4)

    def test___call___w_empty(self):
        not_found = DummyApp()
        environ = _makeEnviron()
        def _start_response(status, headers): pass
        mapper = self._makeOne(not_found)
        result = mapper(environ, _start_response)
        self.assertTrue(result is not_found)
        self.assertTrue(environ['paste.urlmap_object'] is mapper)
        self.assertTrue(result.environ is environ)
        self.assertTrue(result.start_response is _start_response)

    def test___call___w_HTTP_HOST_and_SERVER_NAME(self):
        not_found = DummyApp()
        never_called = DummyApp()
        environ = _makeEnviron(SERVER_NAME='otherdomain.com')
        def _start_response(status, headers): pass
        mapper = self._makeOne(not_found)
        mapper['http://otherdomain.com/'] = never_called
        result = mapper(environ, _start_response)
        self.assertTrue(result is not_found)
        self.assertTrue(never_called.environ is None)

    def test___call___w_only_SERVER_NAME(self):
        not_found = DummyApp()
        called = DummyApp()
        environ = _makeEnviron(SERVER_NAME='Example.com')
        del environ['HTTP_HOST']
        def _start_response(status, headers): pass
        mapper = self._makeOne(not_found)
        mapper['http://example.com/'] = called
        result = mapper(environ, _start_response)
        self.assertTrue(result is called)
        self.assertTrue(not_found.environ is None)

    def test___call___w_port_in_HTTP_HOST(self):
        not_found = DummyApp()
        never_called = DummyApp()
        environ = _makeEnviron()
        environ['HTTP_HOST'] = 'http://example.com:8080'
        def _start_response(status, headers): pass
        mapper = self._makeOne(not_found)
        mapper['http://example.com:8888'] = never_called
        result = mapper(environ, _start_response)
        self.assertTrue(result is not_found)
        self.assertTrue(never_called.environ is None)

    def test___call___wo_port_in_HTTP_HOST_miss(self):
        not_found = DummyApp()
        never_called = DummyApp()
        environ = _makeEnviron()
        def _start_response(status, headers): pass
        mapper = self._makeOne(not_found)
        mapper['http://example.com:8888'] = never_called
        result = mapper(environ, _start_response)
        self.assertTrue(result is not_found)
        self.assertTrue(never_called.environ is None)

    def test___call___wo_port_in_HTTP_HOST_https_scheme(self):
        not_found = DummyApp()
        never_called = DummyApp()
        https = DummyApp()
        environ = _makeEnviron()
        environ['wsgi.url_scheme'] = 'https'
        def _start_response(status, headers): pass
        mapper = self._makeOne(not_found)
        mapper['http://example.com:80'] = never_called
        mapper['http://example.com:443'] = https
        result = mapper(environ, _start_response)
        self.assertTrue(result is https)
        self.assertTrue(never_called.environ is None)

    def test___call___wo_port_in_HTTP_HOST_hit(self):
        not_found = DummyApp()
        shorter = DummyApp()
        longer = DummyApp()
        environ = _makeEnviron(PATH_INFO='/foobar')
        def _start_response(status, headers): pass
        mapper = self._makeOne(not_found)
        mapper['http://example.com:80/foo'] = shorter
        mapper['http://example.com:80/foobar'] = longer
        result = mapper(environ, _start_response)
        self.assertTrue(result is longer)
        self.assertTrue(shorter.environ is None)
        self.assertEqual(environ['SCRIPT_NAME'], '/foobar')
        self.assertEqual(environ['PATH_INFO'], '')

    def test___call___wo_port_in_HTTP_HOST_hit_w_subpath(self):
        not_found = DummyApp()
        shorter = DummyApp()
        longer = DummyApp()
        environ = _makeEnviron(PATH_INFO='/foobar/baz')
        def _start_response(status, headers): pass
        mapper = self._makeOne(not_found)
        mapper['http://example.com:80/foo'] = shorter
        mapper['http://example.com:80/foobar'] = longer
        result = mapper(environ, _start_response)
        self.assertTrue(result is longer)
        self.assertTrue(shorter.environ is None)
        self.assertEqual(environ['SCRIPT_NAME'], '/foobar')
        self.assertEqual(environ['PATH_INFO'], '/baz')


class Test_urlmap_factory(unittest.TestCase):

    def _callFUT(self, loader, global_conf, **local_conf):
        from ..urlmap import urlmap_factory
        return urlmap_factory(loader, global_conf, **local_conf)

    def test_empty_wo_notfound_app(self):
        from ..urlmap import _default_not_found_app
        mapper = self._callFUT(object(), {})
        self.assertEqual(len(mapper), 0)
        self.assertTrue(mapper.not_found_application is _default_not_found_app)

    def test_empty_w_global_notfound_app(self):
        not_found = DummyApp()
        loader = DummyLoader(xxx=not_found)
        gconf = {'not_found_app': 'xxx'}
        before = gconf.copy()
        mapper = self._callFUT(loader, gconf)
        self.assertEqual(len(mapper), 0)
        self.assertTrue(mapper.not_found_application is not_found)
        self.assertEqual(gconf, before)

    def test_empty_w_local_notfound_app(self):
        not_found = DummyApp()
        loader = DummyLoader(yyy=not_found)
        gconf = {'not_found_app': 'xxx'}
        before = gconf.copy()
        mapper = self._callFUT(loader, gconf, not_found_app='yyy')
        self.assertEqual(len(mapper), 0)
        self.assertTrue(mapper.not_found_application is not_found)
        self.assertEqual(gconf, before)

    def test_nonempty(self):
        not_found = DummyApp()
        _APP1, _APP2, _APP3 = DummyApp(), DummyApp(), DummyApp()
        loader = DummyLoader(www=not_found, xxx=_APP1, yyy=_APP2, zzz=_APP3)
        umap = {'/foo': 'xxx', '/foobar': 'yyy', '/foo/bar': 'zzz'}
        mapper = self._callFUT(loader, {}, not_found_app='www', **umap)
        self.assertEqual(len(mapper), 3)
        self.assertTrue(mapper.not_found_application is not_found)
        self.assertTrue(mapper['/foo'] is _APP1)
        self.assertTrue(mapper['/foobar'] is _APP2)
        self.assertTrue(mapper['/foo/bar'] is _APP3)


class DummyApp(object):

    environ = start_response = None

    def __call__(self, environ, start_response):
        self.environ = environ
        self.start_response = start_response
        return self

class DummyLoader(dict):

    def get_app(self, spec, global_conf):
        return self[spec]

def _makeEnviron(**kw):
    environ = {
        'HTTP_HOST': 'example.com',
        'REQUEST_METHOD': 'GET',
        'SCRIPT_NAME': '',
        'PATH_INFO': '/',
        'wsgi.url_scheme': 'http',
    }
    environ.update(kw)
    return environ


class Functests(unittest.TestCase):

    def _makeOne(self):
        from ..urlmap import URLMap

        mapper = URLMap()
        return mapper, TestApp(mapper)

    def test_map(self):

        def _make_app(response_text):
            def app(environ, start_response):
                headers = [('Content-type', 'text/html')]
                start_response('200 OK', headers)
                return [(response_text % environ).encode('utf8')]
            return app

        mapper, app = self._makeOne()
        text = '%s script_name="%%(SCRIPT_NAME)s" path_info="%%(PATH_INFO)s"'
        mapper[''] = _make_app(text % 'root')
        mapper['/foo'] = _make_app(text % 'foo-only')
        mapper['/foo/bar'] = _make_app(text % 'foo:bar')
        mapper['/f'] = _make_app(text % 'f-only')
        res = app.get('/')
        res.mustcontain('root')
        res.mustcontain('script_name=""')
        res.mustcontain('path_info="/"')
        res = app.get('/blah')
        res.mustcontain('root')
        res.mustcontain('script_name=""')
        res.mustcontain('path_info="/blah"')
        res = app.get('/foo/and/more')
        res.mustcontain('script_name="/foo"')
        res.mustcontain('path_info="/and/more"')
        res.mustcontain('foo-only')
        res = app.get('/foo/bar/baz')
        res.mustcontain('foo:bar')
        res.mustcontain('script_name="/foo/bar"')
        res.mustcontain('path_info="/baz"')
        res = app.get('/fffzzz')
        res.mustcontain('root')
        res.mustcontain('path_info="/fffzzz"')
        res = app.get('/f/z/y')
        res.mustcontain('script_name="/f"')
        res.mustcontain('path_info="/z/y"')
        res.mustcontain('f-only')

    def test_404(self):
        mapper, app = self._makeOne()
        res = app.get("/-->%0D<script>alert('xss')</script>", status=404)
        self.assertTrue(b'--><script' not in res.body)
        res = app.get("/--%01><script>", status=404)
        self.assertTrue(b'--\x01><script>' not in res.body)
