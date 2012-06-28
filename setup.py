#!/usr/bin/env python
import os
from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(name='django-adaptors',
      version='0.2.3',
      description='Convert CSV/XML files into python object or django model',
      author='Anthony Tresontani',
      author_email='dev.tresontani@gmail.com',
      long_description=read('README.txt'),
      license="BSD",
      keywords="CSV XML Django adaptor",
      packages=['adaptor'],
      install_requires=[
          'lxml==2.3.4',
          'Django==1.4',
      ],
      classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
    ],
)
