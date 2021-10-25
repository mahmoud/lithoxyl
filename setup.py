"""A systematic approach to application instrumentation, including
logging, semantic profiling, and statistics collection. Very
lightweight, very Pythonic.

(c) 2020 by Mahmoud Hashemi.
BSD-licensed, see LICENSE for more details.
"""

import sys
from setuptools import setup, find_packages


__author__ = 'Mahmoud Hashemi'
__version__ = '21.0.0'
__contact__ = 'mahmoud@hatnote.com'
__url__ = 'https://github.com/mahmoud/lithoxyl'
__license__ = 'BSD'

desc = ('A systematic approach to logging, profiling, and statistics'
        'collection. Very lightweight, very Pythonic.')


if sys.version_info < (2,6):
    raise NotImplementedError("Sorry, lithoxyl only supports Python >=2.6")


setup(name='lithoxyl',
      version=__version__,
      description=desc,
      long_description=__doc__,
      author=__author__,
      author_email=__contact__,
      url=__url__,
      packages=find_packages(),
      install_requires=['boltons>=20.0.0'],
      include_package_data=True,
      zip_safe=False,
      license=__license__,
      platforms='any',
      classifiers=[
          'Intended Audience :: Developers',
          'Topic :: System :: Logging',
          'Topic :: Utilities',
          'Topic :: Software Development :: Libraries :: Application Frameworks',
          'License :: OSI Approved :: BSD License',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: Implementation :: CPython',
          'Programming Language :: Python :: Implementation :: PyPy',
      ]
)


"""
A brief checklist for release:

* tox
* git commit (if applicable)
* Bump setup.py version off of -dev
* git commit -a -m "bump version for x.y.z release"
* python setup.py sdist bdist_wheel upload
* bump docs/conf.py version
* git commit
* git tag -a x.y.z -m "brief summary"
* write CHANGELOG
* git commit
* bump setup.py version onto n+1 dev
* git commit
* git push

"""
