***********************************************
* MapKit 1.2.0
* Author: Nathan Swain
* Copyright: (c) Brigham Young University 2013
* License: BSD 2-Clause
***********************************************

INTRODUCTION

MapKit is a Python module with mapping functions for PostGIS enabled PostgreSQL databases.

DEPENDENCIES

SQLAlchemy
PostGIS enabled PostgreSQL database

To load rasters into the database, you will need raster2pgsql executable that comes with a PostGIS installation

INSTALLATION

easy_install mapkit

or 

pip install mapkit

or 

Clone the source at:

git clone https://github.com/CI-WATER/mapkit.git

and run:

python setup.py install
