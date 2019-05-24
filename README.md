# MapKit
* Author: Nathan Swain, Alan Snow
* Copyright: (c) Brigham Young University 2013
* License: BSD 2-Clause

[![PyPI version](https://badge.fury.io/py/mapkit.svg)](https://badge.fury.io/py/mapkit)

# INTRODUCTION

MapKit is a Python module with mapping functions for PostGIS enabled PostgreSQL databases.


# DEPENDENCIES

* SQLAlchemy
* PostGIS enabled PostgreSQL database

To load rasters into the database, you will need raster2pgsql executable that comes with a PostGIS installation

# INSTALLATION

If you are using Anaconda (https://www.continuum.io/why-anaconda):

```
$ conda install -c conda-forge mapkit
```

Otherwise, you can install through the regular Python methods:
```
$ easy_install mapkit
```
or
```
$ pip install mapkit
```
# DEVELOPER INSTALLATION

Clone the source at:
```
$ git clone https://github.com/CI-WATER/mapkit.git
```
and run:

```
$ python setup.py install
```
