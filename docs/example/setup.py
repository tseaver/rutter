from setuptools import setup

setup(
    name='rutter_example',
    version='0.0',
    install_requires=['pyramid'],
    entry_points="""\
      [paste.app_factory]
      alpha = alpha:main
      bravo = bravo:main
    """
)
