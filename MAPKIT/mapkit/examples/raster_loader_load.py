from mapkit.RasterLoader import RasterLoader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from datetime import datetime

# Setup SQLAlchemy connection
engine = create_engine('postgresql://swainn:(|w@ter@localhost:5432/gsshapy_postgis')
gsshapySessionMaker = sessionmaker(bind=engine)
session = gsshapySessionMaker()

# Initialize raster loader
loader = RasterLoader(engine=engine,
                      raster2pgsql='/Applications/Postgres93.app/Contents/MacOS/bin/raster2pgsql')

# Create list of dictionaries with the raster information rasters to load
rasterPaths = [{'path': '/Users/swainn/projects/post_gis/rasters/combo.idx', 
                'srid': 26912,
                'no-data': 0,
                'timestamp': datetime.today()},
               {'path': '/Users/swainn/projects/post_gis/rasters/luse.idx',
                'srid': 26912,
                'no-data': -1,
                'timestamp': datetime.today()},
               {'path': '/Users/swainn/projects/post_gis/rasters/parkcity.ele',
                'srid': 26912,
                'no-data': 0},
               {'path': '/Users/swainn/projects/post_gis/rasters/parkcity.msk',
                'srid': 26912,
                'no-data': 0},
               {'path': '/Users/swainn/projects/post_gis/rasters/soil.idx',
                'srid': 26912,
                'no-data': -1,
                'timestamp': datetime.today()},
               {'path': '/Users/swainn/projects/post_gis/large_rasters/LittleDellBaseYear.ele',
                'srid': 26912,
                'no-data': 0,
                'timestamp': datetime.today()},
               {'path': '/Users/swainn/projects/post_gis/large_rasters/Soil_Type.idx',
                'srid': 26912,
                'no-data': 0}]


# Execute load method
result = loader.load('test_rasters', rasterPaths)


