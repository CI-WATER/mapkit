from mapkit.RasterConverter import RasterConverter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# For pretty print functionality for debugging
# not recommended for production
import xml.dom.minidom

# Setup SQLAlchemy connection
gsshapyEngine = create_engine('postgresql://swainn:(|w@ter@localhost:5432/gsshapy')
gsshapySessionMaker = sessionmaker(bind=gsshapyEngine)
gsshapySession = gsshapySessionMaker()

# Initialize raster converter
gsshapyConverter = RasterConverter(sqlAlchemySession=gsshapySession)

# Configure RasterConverter instance
colors = [(255, 0, 0),(0, 255, 0),(0, 0, 255)]
colorRamp = RasterConverter.generateCustomColorRamp(colors, 10)

# colorRamp = RasterConverter.generateDefaultColorRamp(RasterConverter.COLOR_RAMP_HUE)
gsshapyConverter.setColorRamp(colorRamp)
    
tableName = 'idx_index_maps'
name = 'Soils Index Maps'
path = '/Users/swainn/projects/post_gis/soil_cluster.kml'

kmlString = gsshapyConverter.getAsKmlClusters(tableName=tableName, 
                                              rasterId=2,
                                              documentName=name)

with open(path, 'w') as f:
    pretty = xml.dom.minidom.parseString(kmlString)
    f.write(pretty.toprettyxml())
#     f.write(kmlString)
