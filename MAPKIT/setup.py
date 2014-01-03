import os

from setuptools import setup, find_packages

requires = [
    'sqlalchemy>=0.7'
    ]

setup(name='mapkit',
      version='1.0.0',
      description='Mapping tools for PostGIS-enabled PostgreSQL databases.',
      long_description='',
      author='Nathan Swain',
      author_email='nathan.swain@byu.net',
      url='https://bitbucket.org/swainn/mapkit',
      license='BSD 2-Clause License',
      keywords='PostGIS, map, GIS',
      packages=find_packages(),
      include_package_data=True,
      install_requires=requires,
      tests_require=requires,
      test_suite=''
      )