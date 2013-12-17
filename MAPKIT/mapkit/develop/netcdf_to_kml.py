from mapkit.RasterConverter import RasterConverter
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


engine = create_engine('postgresql://swainn:(|w@ter@localhost:5432/gis')
Session = sessionmaker(bind=engine)
session = Session()

tableName = 'netcdf_raster'
ramp = 'rainbow'
name = 'NETCDF TEST'
path = '/Users/swainn/projects/netcdf_to_kml/netcdf.kml'

converter = RasterConverter(sqlAlchemySession=session)

# Configure RasterConverter instance
colors = [(255, 0, 0),(0, 255, 0),(0, 0, 255)]
colorRamp = RasterConverter.generateCustomColorRamp(colors, 10)
# colorRamp = RasterConverter.generateDefaultColorRamp(RasterConverter.COLOR_RAMP_HUE)
converter.setColorRamp(colorRamp)
            
kmlString = converter.getAsKmlGrid(tableName=tableName,
                                   rasterId=3,
                                   rasterIdFieldName='rid',
                                   name=name,
                                   rasterType='continuous',
                                   alpha=0.7)

with open(path, 'w') as f:
    f.write(kmlString)


