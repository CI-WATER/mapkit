from mapkit.RasterConverter import RasterConverter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# For pretty print functionality for debugging
# not recommended for production
import xml.dom.minidom
import time, os
from zipfile import ZipFile

# Setup SQLAlchemy connection
gsshapyEngine = create_engine('postgresql://swainn:(|w@ter@localhost:5432/gsshapy_postgis')
gsshapySessionMaker = sessionmaker(bind=gsshapyEngine)
gsshapySession = gsshapySessionMaker()

# Initialize raster converter
gsshapyConverter = RasterConverter(sqlAlchemySession=gsshapySession)

# Configure RasterConverter instance
colors = [(255, 0, 0),(0, 255, 0),(0, 0, 255)]
gsshapyConverter.setCustomColorRamp(colors, 2)
# gsshapyConverter.setDefaultColorRamp(RasterConverter.COLOR_RAMP_HUE)
    
tableName = 'idx_index_maps'
name = 'Soils Index Maps'
directory = '/Users/swainn/projects/post_gis'
archiveName = 'soil_index_png'

# Start timer
start = time.time()

kmlString, binaryPngString = gsshapyConverter.getAsKmlPng(tableName=tableName, 
                                                          rasterId=2,
                                                          documentName=name)


# Create kmz (zip) archive
kmzPath = os.path.join(directory, (archiveName + '.kmz'))

# KML Wrapper path
# PNG file must be called 'raster.png' and located in the same directory as the kml file
# to be recognized by the kml wrapper file

with ZipFile(kmzPath, 'w') as kmz:
    kmz.writestr(archiveName + '.kml', kmlString)
    kmz.writestr('raster.png', binaryPngString)

print 'KML CONVERSION TIME:', time.time()-start

# Use optional return values to write files individually

# Write PNG to file (for debugging)
pngPath = os.path.join(directory, 'raster.png')
  
with open(pngPath, 'wb') as f:
    f.write(binaryPngString)

# Write KML to file (for debugging)
kmlPath = os.path.join(directory, 'debug.kml')
 
with open(kmlPath, 'w') as k:
    pretty = xml.dom.minidom.parseString(kmlString)
    k.write(pretty.toprettyxml())


