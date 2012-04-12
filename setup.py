#!/usr/bin/env python

import glob 

from setuptools import setup

setup(name='glyph-rpc',
      version='0.1-20120412',
      license="MIT License",
      description='glyph-rpc is yet another http rpc library, but it tries to exploit http rather than simply tunnel requests over it.',
      author='tef',
      author_email='tef@twentygototen.org',
      packages=['glyph', 'glyph.resource'],
      #scripts=glob.glob('*.py'),
      test_suite = "tests",
     )

