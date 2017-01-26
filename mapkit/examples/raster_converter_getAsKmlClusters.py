from mapkit.RasterConverter import RasterConverter
from sqlalchemy import create_engine

# For pretty print functionality for debugging
# not recommended for production
# import xml.dom.minidom
import time

# Setup SQLAlchemy connection
engine = create_engine('postgresql://swainn:(|w@ter@localhost:5432/gsshapy_postgis')

tableName = 'map_kit_rasters'
rasterId = 5
name = 'Soils Index Map Clusters'
path = '/Users/swainn/projects/post_gis/map_kit_rasters/soil_cluster.kml'

# Initialize raster converter
converter = RasterConverter(sqlAlchemyEngine=engine)

# Configure RasterConverter instance with custom color ramp
colors = [(255, 0, 0),(0, 255, 0),(0, 0, 255)]
converter.setCustomColorRamp(colors, 10)

# Start timer
start = time.time()

kmlString = converter.getAsKmlClusters(tableName=tableName, 
                                              rasterId=rasterId,
                                              documentName=name)

with open(path, 'w') as f:
#     pretty = xml.dom.minidom.parseString(kmlString)
#     f.write(pretty.toprettyxml())
    f.write(kmlString)

print 'KML CONVERSION TIME:', time.time()-start
