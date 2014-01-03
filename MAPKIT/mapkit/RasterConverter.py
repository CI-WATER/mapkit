'''
********************************************************************************
* Name: RasterConverter
* Author: Nathan Swain
* Created On: November 19, 2013
* Copyright: (c) Brigham Young University 2013
* License: BSD 2-Clause
********************************************************************************
'''
import math
import xml.etree.ElementTree as ET

from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
from sqlalchemy.orm.session import Session

class RasterConverter(object):
    '''
    An instance of RasterConverter can be used to extract PostGIS
    rasters from a database and convert them into different formats
    for visualization.
    '''
    
    # Class variables
    LINE_COLOR = 'FF000000'
    LINE_WIDTH = 1
    MAX_HEX_DECIMAL = 255
    NO_DATA_VALUE_MIN = float(-1.0)
    NO_DATA_VALUE_MAX = float(0.0)
    
    # Color Ramp Identifiers
    COLOR_RAMP_HUE = 0
    COLOR_RAMP_TERRAIN = 1
    COLOR_RAMP_AQUA = 2
    
    def __init__(self, sqlAlchemyEngineOrSession, colorRamp=None):
        '''
        Constructor
        '''
        # Create sqlalchemy session
        if isinstance(sqlAlchemyEngineOrSession, Engine):
            sessionMaker = sessionmaker(bind=sqlAlchemyEngineOrSession)
            self._session = sessionMaker()
        elif isinstance(sqlAlchemyEngineOrSession, Session):
            self._session = sqlAlchemyEngineOrSession        
        
        if not colorRamp:
            self.setDefaultColorRamp(RasterConverter.COLOR_RAMP_HUE)
        else:
            self._colorRamp = colorRamp

    def getAsKmlGrid(self, tableName, rasterId=1, rasterIdFieldName='id', rasterFieldName='raster', alpha=1.0, documentName='default'):
        '''
        Creates a KML file with each cell in the raster represented by a polygon. The result is a vector grid representation of the raster. 
        Note that pixels with values between -1 and 0 are omitted as no data values. Also note that this method only works on the first band.
        Returns the kml document as a string.
        '''
        # Validate alpha
        if not (alpha >= 0 and alpha <= 1.0):
            print "RASTER CONVERSION ERROR: alpha must be between 0.0 and 1.0."
            raise
        
        # Get color ramp and interpolation parameters
        colorRamp, slope, intercept = self.getColorRampInterpolationParameters(self._session, tableName, rasterId, rasterIdFieldName, rasterFieldName, alpha)
        
        # Get polygons for each cell in kml format
        statement = '''
                    SELECT x, y, val, ST_AsKML(geom) AS polygon
                    FROM (
                    SELECT (ST_PixelAsPolygons(%s)).*
                    FROM %s WHERE %s=%s
                    ) AS foo
                    ORDER BY val;
                    ''' % (rasterFieldName, tableName, rasterIdFieldName, rasterId)
        
        result = self._session.execute(statement)
        
        # Initialize KML Document            
        kml = ET.Element('kml', xmlns='http://www.opengis.net/kml/2.2')
        document = ET.SubElement(kml, 'Document')
        docName = ET.SubElement(document, 'name')
        docName.text = documentName
        
        groupValue = -9999999.0
        
        # Add polygons to the kml file with styling
        for row in result:
            # Value will be None if it is a no data value
            if (row.val):
                value = float(row.val)
            else:
                value = None
            
            polygonString = row.polygon
            i = int(row.x)
            j = int(row.y)
            
            # Only create placemarks for values that are no data values
            if (value):
                # Create a new placemark for each group of values
                if (value != groupValue):
                    placemark = ET.SubElement(document, 'Placemark')
                    placemarkName = ET.SubElement(placemark, 'name')
                    placemarkName.text = str(value)
                    
                    # Create style tag and setup styles
                    style = ET.SubElement(placemark, 'Style')
                    
                    # Set polygon line style
                    lineStyle = ET.SubElement(style, 'LineStyle')
                    
                    # Set polygon line color and width
                    lineColor = ET.SubElement(lineStyle, 'color')
                    lineColor.text = self.LINE_COLOR
                    lineWidth = ET.SubElement(lineStyle, 'width')
                    lineWidth.text = str(self.LINE_WIDTH)
                    
                    # Set polygon fill color
                    polyStyle = ET.SubElement(style, 'PolyStyle')
                    polyColor = ET.SubElement(polyStyle, 'color')
                    
                    # Get ramp index for polygon fill color
                    rampIndex = math.trunc(slope * float(value) + intercept)
                    
                    # Convert alpha from 0.0-1.0 decimal to 00-FF string
                    integerAlpha = int(alpha * self.MAX_HEX_DECIMAL)
                    
                    # Get RGB color from color ramp and convert to KML hex ABGR string with alpha
                    integerRGB = colorRamp[rampIndex]
                    hexABGR = '%02X%02X%02X%02X' % (integerAlpha, integerRGB[2], integerRGB[1], integerRGB[0])
                    
                    # Set the polygon fill alpha and color
                    polyColor.text = hexABGR
                    
                    # Create multigeometry tag
                    multigeometry = ET.SubElement(placemark, 'MultiGeometry')
                    
                    # Create the data tag
                    extendedData = ET.SubElement(placemark, 'ExtendedData')
                    
                    # Add value to data
                    valueData = ET.SubElement(extendedData, 'Data', name='value')
                    valueValue = ET.SubElement(valueData, 'value')
                    valueValue.text = str(value)
                    
                    iData = ET.SubElement(extendedData, 'Data', name='i')
                    valueI = ET.SubElement(iData, 'value')
                    valueI.text = str(i)
                    
                    jData = ET.SubElement(extendedData, 'Data', name='j')
                    valueJ = ET.SubElement(jData, 'value')
                    valueJ.text = str(j)
                    
                    groupValue = value              
                
                # Get polygon object from kml string and append to the current multigeometry group
                polygon = ET.fromstring(polygonString)
                multigeometry.append(polygon)                    
        
        return ET.tostring(kml)
    
    def getAsKmlClusters(self, tableName, rasterId=1, rasterIdFieldName='id', rasterFieldName='raster', alpha=1.0, documentName='default'):
        '''
        Creates a KML file where adjacent cells with the same value are clustered together into a polygons. The result is a vector representation 
        of each cluster. Note that pixels with values between -1 and 0 are omitted as no data values. Also note that this method only works on the first band.
        Returns the kml document as a string.
        '''
        
        if not (alpha >= 0 and alpha <= 1.0):
            print "RASTER CONVERSION ERROR: alpha must be between 0.0 and 1.0."
            raise
        
        # Get color ramp and interpolation parameters
        colorRamp, slope, intercept = self.getColorRampInterpolationParameters(self._session, tableName, rasterId, rasterIdFieldName, rasterFieldName, alpha)
        
        # Get a set of polygons representing cluster of adjacent cells with the same value
        statement = '''
                    SELECT val, ST_AsKML(geom) As polygon
                    FROM (
                    SELECT (ST_DumpAsPolygons(%s)).*
                    FROM %s WHERE %s=%s
                    ) As foo
                    ORDER BY val;
                    ''' % (rasterFieldName, tableName, rasterIdFieldName, rasterId)
                    
        result = self._session.execute(statement)
        
        # Initialize KML Document            
        kml = ET.Element('kml', xmlns='http://www.opengis.net/kml/2.2')
        document = ET.SubElement(kml, 'Document')
        docName = ET.SubElement(document, 'name')
        docName.text = documentName
        
        groupValue = -9999999.0
        
        # Add polygons to the kml file with styling
        for row in result:
            # Value will be None if it is a no data value
            if (row.val):
                value = float(row.val)
            else:
                value = None
            
            polygonString = row.polygon
            
            if (value):
                # Create a new placemark for each group of values
                if (value != groupValue):
                    placemark = ET.SubElement(document, 'Placemark')
                    placemarkName = ET.SubElement(placemark, 'name')
                    placemarkName.text = str(value)
                    
                    # Create style tag and setup styles
                    style = ET.SubElement(placemark, 'Style')
                    
                    # Set polygon line style
                    lineStyle = ET.SubElement(style, 'LineStyle')
                    
                    # Set polygon line color and width
                    lineColor = ET.SubElement(lineStyle, 'color')
                    lineColor.text = self.LINE_COLOR
                    lineWidth = ET.SubElement(lineStyle, 'width')
                    lineWidth.text = str(self.LINE_WIDTH)
                    
                    # Set polygon fill color
                    polyStyle = ET.SubElement(style, 'PolyStyle')
                    polyColor = ET.SubElement(polyStyle, 'color')
                    
                    # Get ramp index for polygon fill color
                    rampIndex = math.trunc(slope * float(value) + intercept)
                    
                    # Convert alpha from 0.0-1.0 decimal to 00-FF string
                    integerAlpha = int(alpha * self.MAX_HEX_DECIMAL)
                    
                    # Get RGB color from color ramp and convert to KML hex ABGR string with alpha
                    integerRGB = colorRamp[rampIndex]
                    hexABGR = '%02X%02X%02X%02X' % (integerAlpha, integerRGB[2], integerRGB[1], integerRGB[0])
                    
                    # Set the polygon fill alpha and color
                    polyColor.text = hexABGR
                    
                    # Create multigeometry tag
                    multigeometry = ET.SubElement(placemark, 'MultiGeometry')
                    
                    # Create the data tag
                    extendedData = ET.SubElement(placemark, 'ExtendedData')
                    
                    # Add value to data
                    valueData = ET.SubElement(extendedData, 'Data', name='value')
                    valueValue = ET.SubElement(valueData, 'value')
                    valueValue.text = str(value)
                    
                    groupValue = value              
               
                
                # Get polygon object from kml string and append to the current multigeometry group
                polygon = ET.fromstring(polygonString)
                multigeometry.append(polygon)
                
        return ET.tostring(kml)
    
    def getAsKmlPng(self, tableName, rasterId=1, rasterIdFieldName='id', rasterFieldName='raster', alpha=1.0, documentName='default', drawOrder=0):
        '''
        Creates a KML wrapper and PNG representat of the raster. Returns a string of the kml file contents and
        a binary string of the PNG contents. The color ramp used to generate the PNG is embedded in the ExtendedData 
        tag of the GroundOverlay.
        IMPORTANT: The PNG image is referenced in the kml as 'raster.png', thus it must be written to file with that 
        name for the kml to recognize it.
        '''
        
        # Get the color ramp and parameters
        colorRamp, slope, intercept = self.getColorRampInterpolationParameters(self._session, tableName, rasterId, rasterIdFieldName, rasterFieldName, alpha)
        
        # Use ST_ValueCount to get all unique values
        statement = '''
                    SELECT (pvc).*
                    FROM (SELECT ST_ValueCount({0}) As pvc
                        FROM {1} WHERE {2}={3}) As foo
                        ORDER BY (pvc).value DESC;
                    '''.format(rasterFieldName, tableName, rasterIdFieldName, rasterId)
                    
        result = self._session.execute(statement)
        rampList = []
        
        # Use the color ramp, slope, intercept and value to look up rbg for each value
        for row in result:
            value = row.value
            rampIndex = math.trunc(slope * float(value) + intercept)
            rgb = colorRamp[rampIndex]
            rampList.append('{0} {1} {2} {3} {4}'.format(value, rgb[0], rgb[1], rgb[2], int(alpha * 255)))
        
        # Add a line for the no-data values (nv)
        rampList.append('nv 0 0 0 0')
        
        # Join strings in list to create ramp
        rampString = '\n'.join(rampList)
        
        # Get a PNG representation of the raster
        statement = '''
                    SELECT ST_AsPNG(ST_Transform(ST_ColorMap({0}, 1, '{4}'), 4326, 'Bilinear')) As png
                    FROM {1}
                    WHERE {2}={3};
                    '''.format(rasterFieldName, tableName, rasterIdFieldName, rasterId, rampString)
                    
        result = self._session.execute(statement)
        
        for row in result:
            binaryPNG = row.png
            
        # Determine extents for the KML wrapper file via query
        statement = '''
                    SELECT (foo.metadata).*
                    FROM (
                    SELECT ST_MetaData(ST_Transform({0}, 4326, 'Bilinear')) as metadata 
                    FROM {1}
                    WHERE {2}={3}
                    ) As foo;
                    '''.format(rasterFieldName, tableName, rasterIdFieldName, rasterId)
        
        result = self._session.execute(statement)
        
        for row in result:
            upperLeftY = row.upperlefty
            scaleY = row.scaley
            height = row.height
            
            upperLeftX = row.upperleftx
            scaleX = row.scalex
            width = row.width
        
        north = upperLeftY
        south = upperLeftY + (scaleY * height)
        east = upperLeftX + (scaleX * width)
        west = upperLeftX
        
        # Initialize KML Document            
        kml = ET.Element('kml', xmlns='http://www.opengis.net/kml/2.2')
        document = ET.SubElement(kml, 'Document')
        docName = ET.SubElement(document, 'name')
        docName.text = documentName
        
        # GroundOverlay
        groundOverlay = ET.SubElement(document, 'GroundOverlay')
        overlayName = ET.SubElement(groundOverlay, 'name')
        overlayName.text = 'Overlay'
        
        # DrawOrder
        drawOrderElement = ET.SubElement(groundOverlay, 'drawOrder')
        drawOrderElement.text = str(drawOrder)
        
        # Define Region
        regionElement = ET.SubElement(groundOverlay, 'Region')
        latLonBox = ET.SubElement(regionElement, 'LatLonBox')
        
        northElement = ET.SubElement(latLonBox, 'north')
        northElement.text = str(north)
        
        southElement = ET.SubElement(latLonBox, 'south')
        southElement.text = str(south)
        
        eastElement = ET.SubElement(latLonBox, 'east')
        eastElement.text = str(east)
        
        westElement = ET.SubElement(latLonBox, 'west')
        westElement.text = str(west)
        
        
        # Href to PNG
        iconElement = ET.SubElement(groundOverlay, 'Icon')
        hrefElement = ET.SubElement(iconElement, 'href')
        hrefElement.text = 'raster.png'
        
        # LatLonBox
        latLonBox = ET.SubElement(groundOverlay, 'LatLonBox')
        
        northElement = ET.SubElement(latLonBox, 'north')
        northElement.text = str(north)
        
        southElement = ET.SubElement(latLonBox, 'south')
        southElement.text = str(south)
        
        eastElement = ET.SubElement(latLonBox, 'east')
        eastElement.text = str(east)
        
        westElement = ET.SubElement(latLonBox, 'west')
        westElement.text = str(west)

        # Append ramp to kml file for reference later
        extendedDataElement = ET.SubElement(groundOverlay, 'ExtendedData')
        for ramp in rampList:
            dataElement = ET.SubElement(extendedDataElement, 'Data', name='vrgba')
            dataValueElement = ET.SubElement(dataElement, 'value')
            dataValueElement.text = ramp
        
        return ET.tostring(kml), binaryPNG
       
    def getAsKmlAnimation(self):
        '''
        Return a sequence of rasters with timestamps as a kml with time markers for animation.
        '''
        
    def getAsGrassAsciiRaster(self, tableName, rasterId=1, rasterIdFieldName='id', rasterFieldName='raster', newSRID=None):
        '''
        Returns a string representation of the raster in GRASS ASCII raster format.
        '''
        # Get raster in ArcInfo Grid format
        arcInfoGrid = str(self.getAsGdalRaster(rasterFieldName, tableName, rasterIdFieldName, rasterId, 'AAIGrid', newSRID)).splitlines()
        
        ## Convert arcInfoGrid to GRASS ASCII format ##
        # Get values from heaser which look something this:
        # ncols        67
        # nrows        55
        # xllcorner    425802.32143212341
        # yllcorner    44091450.41551345213
        # cellsize     90.0000000
        # ...
        nCols = int(arcInfoGrid[0].split()[1])
        nRows = int(arcInfoGrid[1].split()[1])
        xLLCorner = float(arcInfoGrid[2].split()[1])
        yLLCorner = float(arcInfoGrid[3].split()[1])
        cellSize = float(arcInfoGrid[4].split()[1])
        
        # Remove old headers
        for i in range(0, 5):
            arcInfoGrid.pop(0)
            
        # Check for NODATA_value row and remove if it is there
        if 'NODATA_value' in arcInfoGrid[0]:
            arcInfoGrid.pop(0)
        
        ## Calculate values for GRASS ASCII headers ##
        # These should look like this:
        # north: 4501028.972140
        # south: 4494548.972140
        # east: 460348.288604
        # west: 454318.288604
        # rows: 72
        # cols: 67
        # ...
        
        # xLLCorner and yLLCorner represent the coordinates for the Lower Left corner of the raster
        north = yLLCorner + (cellSize * nRows)
        south = yLLCorner
        east = xLLCorner + (cellSize * nCols)
        west = xLLCorner
        
        # Create header Lines (the first shall be last and the last shall be first)
        grassHeader = ['cols: %s' % nCols,
                       'rows: %s' % nRows,
                       'west: %s' % west,
                       'east: %s' % east,
                       'south: %s' % south,
                       'north: %s' % north]
        
        # Insert grass headers into the grid
        for header in grassHeader:
            arcInfoGrid.insert(0, header)
        
        # Create string
        arcInfoGridString = '\n'.join(arcInfoGrid)
        return arcInfoGridString
        
        
    def getAsGdalRaster(self, rasterFieldName, tableName, rasterIdFieldName, rasterId, gdalFormat, newSRID=None, **kwargs):
        '''
        Returns a string/buffer representation of the raster in the specified format. Wrapper for 
        ST_AsGDALRaster function in the database.
        '''
        
        # Check gdalFormat
        if not (gdalFormat in RasterConverter.supportedGdalRasterFormats(self._session)):
            print 'FORMAT NOT SUPPORTED: {0} format is not supported in this PostGIS installation.'.format(gdalFormat)
            raise
        
        # Setup srid
        if newSRID:
            srid = ', {0}'.format(newSRID)
        else:
            srid = ''
        
        # Compile options
        if kwargs:
            optionsList = []
            for key, value in kwargs.iteritems():
                kwargString = "'{0}={1}'".format(key, value)
                optionsList.append(kwargString)
            
            optionsString = ','.join(optionsList)
            options = ', ARRAY[{0}]'.format(optionsString)
        else:
            options = ''
        
        # Create statement
        statement = '''
                    SELECT ST_AsGDALRaster({0}, '{1}'{5}{6})
                    FROM {2} WHERE {3}={4};
                    '''.format(rasterFieldName, gdalFormat, tableName, rasterIdFieldName, rasterId,  options, srid)
        
        # Execute query
        result = self._session.execute(statement).scalar()
        
        return result
        
    @classmethod
    def supportedGdalRasterFormats(cls, sqlAlchemyEngineOrSession):
        '''
        Return a list of the supported GDAL raster formats.
        '''
        if isinstance(sqlAlchemyEngineOrSession, Engine):
            # Create sqlalchemy session
            sessionMaker = sessionmaker(bind=sqlAlchemyEngineOrSession)
            session = sessionMaker()
        elif isinstance(sqlAlchemyEngineOrSession, Session):
            session = sqlAlchemyEngineOrSession        
        
        # Execute statment
        statement = 'SELECT * FROM st_gdaldrivers() ORDER BY short_name;'
        
        result = session.execute(statement)
        
        supported = dict()
        
        for row in result:
            supported[row[1]] = {'description': row[2], 'options': row[3]}
            
        return supported
        
    def setColorRamp(self, colorRamp=None):
        '''
        Set the color ramp of the raster converter instance
        '''
        if not colorRamp:
            self._colorRamp = RasterConverter.setDefaultColorRamp(RasterConverter.COLOR_RAMP_HUE)
        else:
            self._colorRamp = colorRamp
              
    def setDefaultColorRamp(self, ramp=COLOR_RAMP_HUE):
        '''
        Returns the color ramp as a list of RGB tuples
        '''
        hue     = [(255, 0, 255), (231, 0, 255), (208, 0, 255), (185, 0, 255), (162, 0, 255), (139, 0, 255), (115, 0, 255), (92, 0, 255), (69, 0, 255), (46, 0, 255), (23, 0, 255),        # magenta to blue
                   (0, 0, 255), (0, 23, 255), (0, 46, 255), (0, 69, 255), (0, 92, 255), (0, 115, 255), (0, 139, 255), (0, 162, 255), (0, 185, 255), (0, 208, 255), (0, 231, 255),          # blue to cyan
                   (0, 255, 255), (0, 255, 231), (0, 255, 208), (0, 255, 185), (0, 255, 162), (0, 255, 139), (0, 255, 115), (0, 255, 92), (0, 255, 69), (0, 255, 46), (0, 255, 23),        # cyan to green
                   (0, 255, 0), (23, 255, 0), (46, 255, 0), (69, 255, 0), (92, 255, 0), (115, 255, 0), (139, 255, 0), (162, 255, 0), (185, 255, 0), (208, 255, 0), (231, 255, 0),          # green to yellow
                   (255, 255, 0), (255, 243, 0), (255, 231, 0), (255, 220, 0), (255, 208, 0), (255, 197, 0), (255, 185, 0), (255, 174, 0), (255, 162, 0), (255, 151, 0), (255, 139, 0),    # yellow to orange
                   (255, 128, 0), (255, 116, 0), (255, 104, 0), (255, 93, 0), (255, 81, 0), (255, 69, 0), (255, 58, 0), (255, 46, 0), (255, 34, 0), (255, 23, 0), (255, 11, 0),            # orange to red
                   (255, 0, 0)]                                                                                                                                                            # red
        
        terrain = [(0, 100, 0), (19, 107, 0), (38, 114, 0), (57, 121, 0), (76, 129, 0), (95, 136, 0), (114, 143, 0), (133, 150, 0), (152, 158, 0), (171, 165, 0), (190, 172, 0),                   # dark green to golden rod yellow
                   (210, 180, 0), (210, 167, 5), (210, 155, 10), (210, 142, 15), (210, 130, 20), (210, 117, 25),                                                                                   # golden rod yellow to orange brown
                   (210, 105, 30), (188, 94, 25), (166, 83, 21), (145, 72, 17), (123, 61, 13), (101, 50, 9),                                                                                       # orange brown to dark brown
                   (80, 40, 5), (95, 59, 27), (111, 79, 50), (127, 98, 73), (143, 118, 95), (159, 137, 118),(175, 157, 141), (191, 176, 164), (207, 196, 186), (223, 215, 209), (239, 235, 232),   # dark brown to white
                   (255, 255, 255)]                                                                                                                                                                # white
        
        aqua = [(150, 255, 255), (136, 240, 250), (122, 226, 245), (109, 212, 240), (95, 198, 235), (81, 184, 230), (68, 170, 225), (54, 156, 220), (40, 142, 215), (27, 128, 210), (13, 114, 205), # aqua to blue
                (0, 100, 200), (0, 94, 195), (0, 89, 191), (0, 83, 187), (0, 78, 182), (0, 72, 178), (0, 67, 174), (0, 61, 170), (0, 56, 165), (0, 50, 161), (0, 45, 157), (0, 40, 153),            # blue to navy blue
                (0, 36, 143), (0, 32, 134), (0, 29, 125), (0, 25, 115), (0, 21, 106), (0, 18, 97), (0, 14, 88), (0, 10, 78), (0, 7, 69), (0, 3, 60), (0, 0, 51)]                                    # navy blue to dark navy blue
        
           
        if (ramp == self.COLOR_RAMP_HUE):
            self._colorRamp = hue
        elif (ramp == self.COLOR_RAMP_TERRAIN):
            self._colorRamp = terrain
        elif (ramp == self.COLOR_RAMP_AQUA):
            self._colorRamp = aqua

    def setCustomColorRamp(self, colors=[], interpolatedPoints=10):
        '''
        Accepts a list of RGB tuples and interpolates between them to create a custom color ramp.
        Returns the color ramp as a list of RGB tuples.
        '''
        if not (isinstance(colors, list)):
            print 'COLOR RAMP GENERATOR WARNING: colors must be passed in as a list of RGB tuples.'
            raise
        
        numColors = len(colors)
        
        colorRamp = []
        
        # Iterate over colors
        for index in range (0, numColors - 1):
            bottomColor = colors[index]
            topColor = colors[index + 1]
            
            colorRamp.append(bottomColor)
            
            # Calculate slopes
            rSlope = (topColor[0] - bottomColor[0]) / float(interpolatedPoints)
            gSlope = (topColor[1] - bottomColor[1]) / float(interpolatedPoints)
            bSlope = (topColor[2] - bottomColor[2]) / float(interpolatedPoints)
            
            # Interpolate colors
            for point in range (1, interpolatedPoints):
                red = int(rSlope * point + bottomColor[0])
                green = int(gSlope * point + bottomColor[1])
                blue = int(bSlope * point + bottomColor[2])
                color = (red, green, blue)
                
                # Make sure the color ramp contains unique colors
                if not (color in colorRamp):
                    colorRamp.append(color)
                
        # Append the last color
        colorRamp.append(colors[-1])
                
        self._colorRamp = colorRamp

    def getColorRampInterpolationParameters(self, session, tableName, rasterId, rasterIdFieldName, rasterFieldName, alpha):
        '''
        Creates color ramp based on min and max values of raster pixels. If pixel value is one of the no data values
        it will be excluded in the color ramp interpolation. Returns colorRamp, slope, intercept
        '''
        # Get min and max for raster band 1
        statement = '''
                SELECT {2}, (stats).min, (stats).max
                FROM (
                SELECT {2}, ST_SummaryStats({0}, 1, true) As stats
                FROM {1}
                WHERE {2}={3}
                ) As foo;
                '''.format(rasterFieldName, tableName, rasterIdFieldName, rasterId)
        result = self._session.execute(statement)
        
        # extract the stats
        for row in result:
            minValue = row.min
            maxValue = row.max
        
        # Set the no data value if min is -1 or 0
        if ((float(minValue) == RasterConverter.NO_DATA_VALUE_MAX) or (float(minValue) == RasterConverter.NO_DATA_VALUE_MIN)):
            statement = '''
                    UPDATE {1} SET {0} = ST_SetBandNoDataValue({0},1,{4})
                    WHERE {2} = {3};
                    '''.format(rasterFieldName, tableName, rasterIdFieldName, rasterId, float(minValue))
            session.execute(statement)
            
            # Pull the stats again with no data value set
            statement = '''
                SELECT {2}, (stats).min, (stats).max
                FROM (
                SELECT {2}, ST_SummaryStats({0}, 1, true) As stats
                FROM {1}
                WHERE {2}={3}
                ) As foo;
                '''.format(rasterFieldName, tableName, rasterIdFieldName, rasterId)
            result = session.execute(statement)
            
            # extract the stats
            for row in result:
                minValue = row.min
                maxValue = row.max
        
        # Map color ramp indicies to values
        colorRamp = self._colorRamp
        minRampIndex = 0.0 # Always zero
        maxRampIndex = float(len(colorRamp) - 1) # Map color ramp indices to values using equation of a line
        
        # Resulting equation will be:
        # rampIndex = slope * value + intercept
        if minValue != maxValue:
            slope = (maxRampIndex - minRampIndex) / (maxValue - minValue)
            intercept = maxRampIndex - (slope * maxValue)
        else:
            slope = 0
            intercept = minRampIndex
        
        # Return color ramp, slope, and intercept to interpolate by value
        return colorRamp, slope, intercept

            
        
        
                                                                                                         
        
   
   
