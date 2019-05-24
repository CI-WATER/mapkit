from setuptools import setup, find_packages
import mapkit

requires = [
    'sqlalchemy',
    'requests',
    'epsg-ident'
]

setup(name='mapkit',
      version=mapkit.__version__,
      description='Mapping tools for PostGIS-enabled PostgreSQL databases.',
      long_description='',
      author='Nathan Swain',
      author_email='nathan.swain@byu.net',
      url='https://github.com/CI-WATER/mapkit',
      license='BSD 2-Clause License',
      keywords='PostGIS, map, GIS',
      packages=find_packages(),
      include_package_data=True,
      install_requires=requires,
      tests_require=requires,
      test_suite=''
      )
