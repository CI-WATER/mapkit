from mapkit.RasterConverter import RasterConverter
from sqlalchemy import create_engine

# Setup SQLAlchemy connection
engine = create_engine('postgresql://swainn:(|w@ter@localhost:5432/gsshapy_postgis')

tableName = 'map_kit_rasters'
rasterId = 5
path = '/Users/swainn/projects/post_gis/map_kit_rasters/soil_cluster.kml'

# Get supported gdal raster formats
gdalFormats = RasterConverter.supportedGdalRasterFormats(engine)

for key, value in gdalFormats.items():
    print key, value

# Configure raster converter
converter = RasterConverter(engine)

# Convert PostGIS raster to GDAL format
result = converter.getAsGdalRaster(rasterFieldName='raster',
                                   tableName=tableName,
                                   rasterIdFieldName='id',
                                   rasterId=rasterId,
                                   gdalFormat='JPEG',
                                   QUALITY=50)

# Convert PostGIS raster to GRASS ASCII Grid format
result = converter.getAsGrassAsciiRaster(rasterFieldName='raster',
                                         tableName=tableName,
                                         rasterIdFieldName='id',
                                         rasterId=rasterId)

print result


