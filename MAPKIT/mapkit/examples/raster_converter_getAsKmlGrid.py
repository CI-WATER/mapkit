from mapkit.RasterConverter import RasterConverter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# For pretty print functionality for debugging
# not recommended for production
import xml.dom.minidom

# Setup SQLAlchemy connection
engine = create_engine('postgresql://swainn:(|w@ter@localhost:5432/gis')
Session = sessionmaker(bind=engine)
session = Session()

# Initialize raster converter
converter = RasterConverter(sqlAlchemySession=session)

# Configure RasterConverter instance
colors = [(255, 0, 0),(0, 255, 0),(0, 0, 255)]
colorRamp = RasterConverter.generateCustomColorRamp(colors, 10)

# colorRamp = RasterConverter.generateDefaultColorRamp(RasterConverter.COLOR_RAMP_HUE)
converter.setColorRamp(colorRamp)
            
tableName = 'netcdf_raster'
name = 'NETCDF TEST'
path = '/Users/swainn/projects/netcdf_to_kml/netcdf.kml'

kmlString = converter.getAsKmlGrid(tableName=tableName,
                                   rasterId=3,
                                   rasterIdFieldName='rid',
                                   name=name,
                                   rasterType='continuous',
                                   alpha=0.7)

with open(path, 'w') as f:
#     pretty = xml.dom.minidom.parseString(kmlString)
#     f.write(pretty.toprettyxml())
    f.write(kmlString)
