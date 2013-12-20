from mapkit.RasterConverter import RasterConverter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# For pretty print functionality for debugging
# not recommended for production
import xml.dom.minidom
import time

# Setup SQLAlchemy connection
gsshapyEngine = create_engine('postgresql://swainn:(|w@ter@localhost:5432/gsshapy_postgis')
gsshapySessionMaker = sessionmaker(bind=gsshapyEngine)
gsshapySession = gsshapySessionMaker()

# Initialize raster converter
gsshapyConverter = RasterConverter(sqlAlchemySession=gsshapySession)

# Configure RasterConverter instance
colors = [(255, 0, 0),(0, 255, 0),(0, 0, 255)]
gsshapyConverter.setCustomColorRamp(colors, 10)
    
tableName = 'idx_index_maps'
name = 'Soils Index Maps'
path = '/Users/swainn/projects/post_gis/soil_png.kml'

# Start timer
start = time.time()

kmlString = gsshapyConverter.getAsKmlPng()

with open(path, 'w') as f:
#     pretty = xml.dom.minidom.parseString(kmlString)
#     f.write(pretty.toprettyxml())
    f.write(kmlString)

print 'KML CONVERSION TIME:', time.time()-start
