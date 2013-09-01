"""
    lithoxyl
    ~~~~~~~~

    A systematic approach to logging, profiling, and statistics
    collection. Very lightweight, very Pythonic.

    :copyright: (c) 2013 by Mahmoud Hashemi
    :license: BSD, see LICENSE for more details.

"""

import sys
from setuptools import setup


__author__ = 'Mahmoud Hashemi'
__version__ = '0.0.5'
__contact__ = 'mahmoudrhashemi@gmail.com'
__url__ = 'https://github.com/mahmoud/lithoxyl'
__license__ = 'BSD'

desc = ('A systematic approach to logging, profiling, and statistics'
        'collection. Very lightweight, very Pythonic.')


if sys.version_info < (2,6):
    raise NotImplementedError("Sorry, lithoxyl only supports Python >=2.6")

if sys.version_info >= (3,):
    raise NotImplementedError("lithoxyl Python 3 support en route to your location")

setup(name='lithoxyl',
      version=__version__,
      description=desc,
      long_description=__doc__,
      author=__author__,
      author_email=__contact__,
      url=__url__,
      packages=['lithoxyl',
                'lithoxyl.tests'],
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
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7', ]
      )
