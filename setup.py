#!/usr/bin/env python

import glob 

from setuptools import setup

setup(name='glyph-rpc',
      version='0.1-20120317',
      license="MIT License",
      description='glyph-rpc is well behaved rpc over http with callbacks',
      author='tef',
      author_email='tef@twentygototen.org',
      packages=['glyph'],
      #scripts=glob.glob('*.py'),
      test_suite = "tests",
     )

