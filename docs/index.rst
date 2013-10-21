:mod:`rutter`:  Python3-compatible WSGI composite
=================================================

:mod:`rutter` forks the :mod:`paste.urlmap` module in order to provide
a Python3-compatible impolementation, as well as the improved test coverage
needed to support using the module across all supported Python versions.

The primary export of :mod:`rutter` is the :class:`rutter.urlmap.URLMap`
class.  :class:`~rutter.urlmap.URLMap` instances are dictionary-like objects
which dispatch to WSGI applications based on the URL.

The keys in a :class:`~rutter.urlmap.URLMap` are URL patterns, which match
as prefixes of the request URL (e.g., like ``PATH_INFO.startswith(key)``).
Its values are WSGI applications to which matching requests are dispatched.
On finding a match, the :class:`~rutter.urlmap.URLMap` adjusts the
:envvar:`SCRIPT_NAME` and :envvar:`PATH_INFO` environmental variables to
indicate the new context.

URL Matching Rules
------------------

- URLs are matched most-specific-first, i.e., longest URL first.

- URL prefixes can also include domains, e.g. http://blah.com/foo.  Domains
  can also be specified as tuples ('blah.com', '/foo').

- If a given pattern includes a domain, its path will only be tested if the
  :envvar:`HTTP_HOST` environment variable matches.

- Patterns which do not have domains will be tested only if no domain-specifc
  pattern matches.

Examples
--------

Sample Applications
~~~~~~~~~~~~~~~~~~~

Assume we want to serve two WSGI applications provided by separate modules,
:mod:`alpha`:

.. literalinclude:: example/alpha.py

and :mod:`bravo`.

.. literalinclude:: example/bravo.py

.. note::

   Although these examples use :mod:`pyramid`;  any WSGI-compliant application
   can be used as a dispatch target.

Imperative Configuration in Python
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: example/imperative.py

Assuming that :mod:`alpha` and :mod:`bravo` are importable, along with
:mod:`rutter`, we can run this application:

.. code-block:: sh

   $ /path/to/python example/imperative.py

and then visit the two applications at http://localhost:6543/alpha and
http://localhost:6543/bravo.

Declarative Configuration using :mod:`paste.deploy` INI files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Assuming that we have a :mod:`paste.deploy`-compatible server starter
(such as the :command:`pserve` script installed by :mod:`pyramid`), we can
configure the `:class:`~rutter.urlmap.URLMap` via an INI file:

.. literalinclude:: example/development.ini

And then run the composite application using the starter:

.. code-block:: sh

   $ /path/to/pserve example/development.ini

The two applications are again available at http://localhost:6543/alpha and
http://localhost:6543/bravo.
