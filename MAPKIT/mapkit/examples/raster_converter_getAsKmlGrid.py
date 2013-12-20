from mapkit.RasterConverter import RasterConverter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# For pretty print functionality for debugging
# not recommended for production
import xml.dom.minidom
import time

# Setup SQLAlchemy connection
engine = create_engine('postgresql://swainn:(|w@ter@localhost:5432/gsshapy_postgis')
Session = sessionmaker(bind=engine)
session = Session()

# Initialize raster converter
converter = RasterConverter(sqlAlchemySession=session)
converter.setDefaultColorRamp(RasterConverter.COLOR_RAMP_TERRAIN)
            
tableName = 'raster_maps'
name = 'Park City Elevation'
path = '/Users/swainn/projects/post_gis/ele_terrain.kml'


# Start timer
start = time.time()

kmlString = converter.getAsKmlGrid(tableName=tableName,
                                   rasterId=2,
                                   documentName=name)

with open(path, 'w') as f:
#     pretty = xml.dom.minidom.parseString(kmlString)
#     f.write(pretty.toprettyxml())
    f.write(kmlString)

print 'KML CONVERSION TIME:', time.time()-start