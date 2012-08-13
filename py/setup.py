#!/usr/bin/env python

import glob 

from setuptools import setup

import os.path, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

setup(name='hyperglyph',
      version='0.9-20120813',
      license="MIT License",
      description='hyperglyph is ducked typed ipc over http',
      author='tef',
      author_email='tef@twentygototen.org',
      packages=['glyph', 'glyph.resource'],
      #scripts=glob.glob('*.py'),
      test_suite = "tests",
     )

