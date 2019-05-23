"""
********************************************************************************
* Name: RasterConverter
* Author: Nathan Swain
* Created On: November 19, 2013
* Copyright: (c) Brigham Young University 2013
* License: BSD 2-Clause
********************************************************************************
"""
import xml.etree.ElementTree as ET

from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
from sqlalchemy.orm.session import Session

from mapkit.ColorRampGenerator import ColorRampGenerator, ColorRampEnum


class RasterConverter(object):
    """
    An instance of RasterConverter can be used to extract PostGIS
    rasters from a database and convert them into different formats
    for visualization.
    """

    # Class variables
    LINE_COLOR = 'FF000000'
    LINE_WIDTH = 1
    MAX_HEX_DECIMAL = 255
    NO_DATA_VALUE_MIN = float(-1.0)
    NO_DATA_VALUE_MAX = float(0.0)
    GDAL_ASCII_DATA_TYPES = ['Int32', 'Float32', 'Float64']

    def __init__(self, sqlAlchemyEngineOrSession, colorRamp=None):
        """
        Constructor
        """
        # Create sqlalchemy session
        if isinstance(sqlAlchemyEngineOrSession, Engine):
            sessionMaker = sessionmaker(bind=sqlAlchemyEngineOrSession)
            self._session = sessionMaker()
        elif isinstance(sqlAlchemyEngineOrSession, Session):
            self._session = sqlAlchemyEngineOrSession

        if not colorRamp:
            self.setDefaultColorRamp(ColorRampEnum.COLOR_RAMP_HUE)
        else:
            self._colorRamp = colorRamp

    def getAsKmlGrid(self, tableName, rasterId=1, rasterIdFieldName='id', rasterFieldName='raster', documentName='default', alpha=1.0, noDataValue=0, discreet=False):
        """
        Creates a KML file with each cell in the raster represented by a polygon. The result is a vector grid representation of the raster.
        Note that pixels with values between -1 and 0 are omitted as no data values. Also note that this method only works on the first band.
        Returns the kml document as a string.
        """
        # Validate alpha
        if not (alpha >= 0 and alpha <= 1.0):
            raise ValueError("RASTER CONVERSION ERROR: alpha must be between 0.0 and 1.0.")

        # Get the color ramp and parameters
        minValue, maxValue = self.getMinMaxOfRasters(session=self._session,
                                                     table=tableName,
                                                     rasterIds=(str(rasterId), ),
                                                     rasterIdField=rasterIdFieldName,
                                                     rasterField=rasterFieldName,
                                                     noDataValue=noDataValue)

        mappedColorRamp = ColorRampGenerator.mapColorRampToValues(colorRamp=self._colorRamp,
                                                                  minValue=minValue,
                                                                  maxValue=maxValue,
                                                                  alpha=alpha)

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
        uniqueValues = []

        # Add polygons to the kml file with styling
        for row in result:
            # Value will be None if it is a no data value
            if row.val:
                value = float(row.val)
            else:
                value = None

            polygonString = row.polygon
            i = int(row.x)
            j = int(row.y)

            # Only create placemarks for values that are no data values
            if value:
                # Collect unique values
                if value not in uniqueValues:
                    uniqueValues.append(value)

                # Create a new placemark for each group of values
                if value != groupValue:
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

                    # Convert alpha from 0.0-1.0 decimal to 00-FF string
                    integerAlpha = mappedColorRamp.getAlphaAsInteger()

                    # Get RGB color from color ramp and convert to KML hex ABGR string with alpha
                    integerRGB = mappedColorRamp.getColorForValue(value)
                    hexABGR = '%02X%02X%02X%02X' % (integerAlpha,
                                                    integerRGB[mappedColorRamp.B],
                                                    integerRGB[mappedColorRamp.G],
                                                    integerRGB[mappedColorRamp.R])

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

        if not discreet:
            # Embed the color ramp in SLD format
            document.append(ET.fromstring(mappedColorRamp.getColorMapAsContinuousSLD()))
        else:
            # Sort the unique values
            uniqueValues.sort()
            document.append(ET.fromstring(mappedColorRamp.getColorMapAsDiscreetSLD(uniqueValues)))

        return ET.tostring(kml)

    def getAsKmlClusters(self, tableName, rasterId=1, rasterIdFieldName='id', rasterFieldName='raster', documentName='default', alpha=1.0,  noDataValue=0, discreet=False):
        """
        Creates a KML file where adjacent cells with the same value are clustered together into a polygons. The result is a vector representation
        of each cluster. Note that pixels with values between -1 and 0 are omitted as no data values. Also note that this method only works on the first band.
        Returns the kml document as a string.
        """

        if not (alpha >= 0 and alpha <= 1.0):
            raise ValueError("RASTER CONVERSION ERROR: alpha must be between 0.0 and 1.0.")

        # Get the color ramp and parameters
        minValue, maxValue = self.getMinMaxOfRasters(session=self._session,
                                                     table=tableName,
                                                     rasterIds=(str(rasterId), ),
                                                     rasterIdField=rasterIdFieldName,
                                                     rasterField=rasterFieldName,
                                                     noDataValue=noDataValue)

        mappedColorRamp = ColorRampGenerator.mapColorRampToValues(colorRamp=self._colorRamp,
                                                                  minValue=minValue,
                                                                  maxValue=maxValue,
                                                                  alpha=alpha)

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
        uniqueValues = []

        # Add polygons to the kml file with styling
        for row in result:
            # Value will be None if it is a no data value
            if row.val:
                value = float(row.val)
            else:
                value = None

            polygonString = row.polygon

            if value:
                # Collect unique values
                if value not in uniqueValues:
                    uniqueValues.append(value)

                # Create a new placemark for each group of values
                if value != groupValue:
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

                    # Convert alpha from 0.0-1.0 decimal to 00-FF string
                    integerAlpha = mappedColorRamp.getAlphaAsInteger()

                    # Get RGB color from color ramp and convert to KML hex ABGR string with alpha
                    integerRGB = mappedColorRamp.getColorForValue(value)
                    hexABGR = '%02X%02X%02X%02X' % (integerAlpha,
                                                    integerRGB[mappedColorRamp.B],
                                                    integerRGB[mappedColorRamp.G],
                                                    integerRGB[mappedColorRamp.R])

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

        if not discreet:
            # Embed the color ramp in SLD format
            document.append(ET.fromstring(mappedColorRamp.getColorMapAsContinuousSLD()))
        else:
            # Sort the unique values
            uniqueValues.sort()
            document.append(ET.fromstring(mappedColorRamp.getColorMapAsDiscreetSLD(uniqueValues)))

        return ET.tostring(kml)

    def getAsKmlPng(self, tableName, rasterId=1, rasterIdFieldName='id', rasterFieldName='raster', documentName='default',
                    alpha=1.0,  drawOrder=0, noDataValue=0, cellSize=None, resampleMethod='NearestNeighbour', discreet=False):
        """
        Creates a KML wrapper and PNG represent of the raster. Returns a string of the kml file contents and
        a binary string of the PNG contents. The color ramp used to generate the PNG is embedded in the ExtendedData
        tag of the GroundOverlay.
        IMPORTANT: The PNG image is referenced in the kml as 'raster.png', thus it must be written to file with that
        name for the kml to recognize it.
        """

        # Get the color ramp and parameters
        minValue, maxValue = self.getMinMaxOfRasters(session=self._session,
                                                     table=tableName,
                                                     rasterIds=(str(rasterId), ),
                                                     rasterIdField=rasterIdFieldName,
                                                     rasterField=rasterFieldName,
                                                     noDataValue=noDataValue)

        mappedColorRamp = ColorRampGenerator.mapColorRampToValues(colorRamp=self._colorRamp,
                                                                  minValue=minValue,
                                                                  maxValue=maxValue,
                                                                  alpha=alpha)

        # Join strings in list to create ramp
        rampString = mappedColorRamp.getPostGisColorRampString()

        # Get a PNG representation of the raster
        result = self.getRastersAsPngs(session=self._session,
                                       tableName=tableName,
                                       rasterIds=(str(rasterId),),
                                       postGisRampString=rampString,
                                       rasterField=rasterFieldName,
                                       rasterIdField=rasterIdFieldName,
                                       cellSize=cellSize,
                                       resampleMethod=resampleMethod)

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

        if not discreet:
            # Embed the color ramp in SLD format
            document.append(ET.fromstring(mappedColorRamp.getColorMapAsContinuousSLD()))
        else:
            # Determine values for discreet color ramp
            statement = '''
                        SELECT (pvc).*
                        FROM (
                              SELECT ST_ValueCount({0}) as pvc
                              FROM {1}
                              WHERE {2}={3}
                             ) As foo
                        ORDER BY (pvc).value;
                        '''.format(rasterFieldName, tableName, rasterIdFieldName, rasterId)

            result = self._session.execute(statement)

            values = []
            for row in result:
                values.append(row.value)

            document.append(ET.fromstring(mappedColorRamp.getColorMapAsDiscreetSLD(values)))

        return ET.tostring(kml), binaryPNG



    def getAsKmlGridAnimation(self, tableName, timeStampedRasters=[], rasterIdFieldName='id', rasterFieldName='raster',
                              documentName='default', alpha=1.0,  noDataValue=0, discreet=False):
        """
        Return a sequence of rasters with timestamps as a kml with time markers for animation.

        :param tableName: Name of the table to extract rasters from
        :param timeStampedRasters: List of dictionaries with keys: rasterId, dateTime
               rasterId = a unique integer identifier used to locate the raster (usually value of primary key column)
               dateTime = a datetime object representing the time the raster occurs

               e.g:
               timeStampedRasters = [{ 'rasterId': 1, 'dateTime': datetime(1970, 1, 1)},
                                     { 'rasterId': 2, 'dateTime': datetime(1970, 1, 2)},
                                     { 'rasterId': 3, 'dateTime': datetime(1970, 1, 3)}]

        :param rasterIdFieldName: Name of the id field for rasters (usually the primary key field)
        :param rasterFieldName: Name of the field where rasters are stored (of type raster)
        :param documentName: The name to give to the KML document (will be listed in legend under this name)
        :param alpha: The transparency to apply to each raster cell
        :param noDataValue: The value to be used as the no data value (default is 0)

        :rtype : string
        """

        # Validate alpha
        if not (alpha >= 0 and alpha <= 1.0):
            raise ValueError("RASTER CONVERSION ERROR: alpha must be between 0.0 and 1.0.")

        rasterIds = []

        for timeStampedRaster in timeStampedRasters:
            # Validate dictionary
            if 'rasterId' not in timeStampedRaster:
                raise ValueError('RASTER CONVERSION ERROR: rasterId must be provided for each raster.')
            elif 'dateTime' not in timeStampedRaster:
                raise ValueError('RASTER CONVERSION ERROR: dateTime must be provided for each raster.')

            rasterIds.append(str(timeStampedRaster['rasterId']))

        # One color ramp to rule them all
        # Get a single color ramp that is based on the range of values in all the rasters
        minValue, maxValue = self.getMinMaxOfRasters(session=self._session,
                                                     table=tableName,
                                                     rasterIds=rasterIds,
                                                     rasterIdField=rasterIdFieldName,
                                                     rasterField=rasterFieldName,
                                                     noDataValue=noDataValue)

        mappedColorRamp = ColorRampGenerator.mapColorRampToValues(colorRamp=self._colorRamp,
                                                                  minValue=minValue,
                                                                  maxValue=maxValue,
                                                                  alpha=alpha)



        # Default to time delta to None
        deltaTime = None

        # Calculate delta time between images if more than one
        time1 = timeStampedRasters[0]['dateTime']

        if len(timeStampedRasters) >= 2:
            time2 = timeStampedRasters[1]['dateTime']
            deltaTime = time2 - time1

        # Initialize KML Document
        kml = ET.Element('kml', xmlns='http://www.opengis.net/kml/2.2')
        document = ET.SubElement(kml, 'Document')
        docName = ET.SubElement(document, 'name')
        docName.text = documentName

        if not discreet:
            # Embed the color ramp in SLD format
            document.append(ET.fromstring(mappedColorRamp.getColorMapAsContinuousSLD()))
        else:
            values = []
            document.append(ET.fromstring(mappedColorRamp.getColorMapAsDiscreetSLD(values)))

        # Apply special style to hide legend items
        style = ET.SubElement(document, 'Style', id='check-hide-children')
        listStyle = ET.SubElement(style, 'ListStyle')
        listItemType = ET.SubElement(listStyle, 'listItemType')
        listItemType.text = 'checkHideChildren'
        styleUrl = ET.SubElement(document, 'styleUrl')
        styleUrl.text = '#check-hide-children'

        # Collect unique values
        uniqueValues = []

        # Retrieve the rasters and styles
        for timeStampedRaster in timeStampedRasters:
            # Extract variables
            rasterId = timeStampedRaster['rasterId']

            if deltaTime:
                dateTime = timeStampedRaster['dateTime']
                prevDateTime = dateTime - deltaTime

            # Get polygons for each cell in kml format
            statement = '''
                        SELECT x, y, val, ST_AsKML(geom) AS polygon
                        FROM (
                        SELECT (ST_PixelAsPolygons({0})).*
                        FROM {1} WHERE {2}={3}
                        ) AS foo
                        ORDER BY val;
                        '''.format(rasterFieldName, tableName, rasterIdFieldName, rasterId)

            result = self._session.execute(statement)

            # Set initial group value
            groupValue = -9999999.0

            # Add polygons to the kml file with styling
            for row in result:
                # Value will be None if it is a no data value
                if row.val:
                    value = float(row.val)
                else:
                    value = None

                polygonString = row.polygon
                i = int(row.x)
                j = int(row.y)

                # Only create placemarks for values that are not no data values
                if value:
                    if value not in uniqueValues:
                        uniqueValues.append(value)

                    # Create a new placemark for each group of values
                    if value != groupValue:
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

                        # Convert alpha from 0.0-1.0 decimal to 00-FF string
                        integerAlpha = mappedColorRamp.getAlphaAsInteger()

                        # Get RGB color from color ramp and convert to KML hex ABGR string with alpha
                        integerRGB = mappedColorRamp.getColorForValue(value)
                        hexABGR = '%02X%02X%02X%02X' % (integerAlpha,
                                                        integerRGB[mappedColorRamp.B],
                                                        integerRGB[mappedColorRamp.G],
                                                        integerRGB[mappedColorRamp.R])

                        # Set the polygon fill alpha and color
                        polyColor.text = hexABGR

                        if deltaTime:
                            # Create TimeSpan tag
                            timeSpan = ET.SubElement(placemark, 'TimeSpan')

                            # Create begin and end tags
                            begin = ET.SubElement(timeSpan, 'begin')
                            begin.text = prevDateTime.strftime('%Y-%m-%dT%H:%M:%S')
                            end = ET.SubElement(timeSpan, 'end')
                            end.text = dateTime.strftime('%Y-%m-%dT%H:%M:%S')

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

                        if deltaTime:
                            tData = ET.SubElement(extendedData, 'Data', name='t')
                            valueT = ET.SubElement(tData, 'value')
                            valueT.text = dateTime.strftime('%Y-%m-%dT%H:%M:%S')

                        groupValue = value

                    # Get polygon object from kml string and append to the current multigeometry group
                    polygon = ET.fromstring(polygonString)
                    multigeometry.append(polygon)

        if not discreet:
            # Embed the color ramp in SLD format
            document.append(ET.fromstring(mappedColorRamp.getColorMapAsContinuousSLD()))
        else:
            # Sort the unique values
            uniqueValues.sort()
            document.append(ET.fromstring(mappedColorRamp.getColorMapAsDiscreetSLD(uniqueValues)))

        return ET.tostring(kml)



    def getAsKmlPngAnimation(self, tableName, timeStampedRasters=[], rasterIdFieldName='id', rasterFieldName='raster',
                             documentName='default', noDataValue=0, alpha=1.0, drawOrder=0, cellSize=None,
                             resampleMethod='NearestNeighbour', discreet=False):
        """
        Return a sequence of rasters with timestamps as a kml with time markers for animation.

        :param tableName: Name of the table to extract rasters from
        :param timeStampedRasters: List of dictionaries with keys: rasterId, dateTime
               rasterId = a unique integer identifier used to locate the raster (usually value of primary key column)
               dateTime = a datetime object representing the time the raster occurs

               e.g:
               timeStampedRasters = [{ 'rasterId': 1, 'dateTime': datetime(1970, 1, 1)},
                                     { 'rasterId': 2, 'dateTime': datetime(1970, 1, 2)},
                                     { 'rasterId': 3, 'dateTime': datetime(1970, 1, 3)}]

        :param rasterIdFieldName: Name of the id field for rasters (usually the primary key field)
        :param rasterFieldName: Name of the field where rasters are stored (of type raster)
        :param documentName: The name to give to the KML document (will be listed in legend under this name)
        :param noDataValue: The value to be used as the no data value (default is 0)
        :param alpha: The transparency to apply to each raster cell
        :param drawOrder: The draw order determines the order images are stacked if multiple are showing.
        :param cellSize: Specify this parameter to resample the rasters to a different size the cells (e.g.: 30 to
                         resample to cells with dimensions 30 x 30 in units of the raster spatial reference system).
                         NOTE: the processing time increases exponentially with shrinking cellSize values.

        :rtype : (string, list)

        """


        if not self.isNumber(noDataValue):
            raise ValueError('RASTER CONVERSION ERROR: noDataValue must be a number.')

        if not self.isNumber(drawOrder):
            raise ValueError('RASTER CONVERSION ERROR: drawOrder must be a number.')

        if not (alpha >= 0 and alpha <= 1.0):
            raise ValueError("RASTER CONVERSION ERROR: alpha must be between 0.0 and 1.0.")


        # Extract raster Ids and validate
        rasterIds = []

        for timeStampedRaster in timeStampedRasters:
            # Validate dictionary
            if 'rasterId' not in timeStampedRaster:
                raise ValueError('RASTER CONVERSION ERROR: rasterId must be provided for each raster.')
            elif 'dateTime' not in timeStampedRaster:
                raise ValueError('RASTER CONVERSION ERROR: dateTime must be provided for each raster.')

            rasterIds.append(str(timeStampedRaster['rasterId']))

        # Get the color ramp and parameters
        minValue, maxValue = self.getMinMaxOfRasters(session=self._session,
                                                     table=tableName,
                                                     rasterIds=rasterIds,
                                                     rasterIdField=rasterIdFieldName,
                                                     rasterField=rasterFieldName,
                                                     noDataValue=noDataValue)

        mappedColorRamp = ColorRampGenerator.mapColorRampToValues(colorRamp=self._colorRamp,
                                                                  minValue=minValue,
                                                                  maxValue=maxValue,
                                                                  alpha=alpha)

        # Join strings in list to create ramp
        rampString = mappedColorRamp.getPostGisColorRampString()


        # Get a PNG representation of each raster
        result = self.getRastersAsPngs(session=self._session,
                                       tableName=tableName,
                                       rasterIds=rasterIds,
                                       postGisRampString=rampString,
                                       rasterField=rasterFieldName,
                                       rasterIdField=rasterIdFieldName,
                                       cellSize=cellSize,
                                       resampleMethod=resampleMethod)

        binaryPNGs = []

        for row in result:
            binaryPNGs.append(row.png)

        # Determine extents for the KML wrapper file via query
        statement = '''
                    SELECT (foo.metadata).*
                    FROM (
                    SELECT ST_MetaData(ST_Transform({0}, 4326, 'Bilinear')) as metadata
                    FROM {1}
                    WHERE {2}={3}
                    ) As foo;
                    '''.format(rasterFieldName, tableName, rasterIdFieldName, rasterIds[0])

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

        # Default to time delta to None
        deltaTime = None

        # Calculate delta time between images if more than one
        time1 = timeStampedRasters[0]['dateTime']

        if len(timeStampedRasters) >= 2:
            time2 = timeStampedRasters[1]['dateTime']
            deltaTime = time2 - time1

        # Initialize KML Document
        kml = ET.Element('kml', xmlns='http://www.opengis.net/kml/2.2')
        document = ET.SubElement(kml, 'Document')
        docName = ET.SubElement(document, 'name')
        docName.text = documentName

        if not discreet:
            # Embed the color ramp in SLD format
            document.append(ET.fromstring(mappedColorRamp.getColorMapAsContinuousSLD()))
        else:
            values = []
            document.append(ET.fromstring(mappedColorRamp.getColorMapAsDiscreetSLD(values)))

        # Apply special style to hide legend items
        style = ET.SubElement(document, 'Style', id='check-hide-children')
        listStyle = ET.SubElement(style, 'ListStyle')
        listItemType = ET.SubElement(listStyle, 'listItemType')
        listItemType.text = 'checkHideChildren'
        styleUrl = ET.SubElement(document, 'styleUrl')
        styleUrl.text = '#check-hide-children'

        for index, timeStampedRaster in enumerate(timeStampedRasters):
            # Extract variable
            if deltaTime:
                dateTime = timeStampedRaster['dateTime']
                prevDateTime = dateTime - deltaTime


            # GroundOverlay
            groundOverlay = ET.SubElement(document, 'GroundOverlay')
            overlayName = ET.SubElement(groundOverlay, 'name')
            overlayName.text = 'Overlay'

            if deltaTime:
                # Create TimeSpan tag
                timeSpan = ET.SubElement(groundOverlay, 'TimeSpan')

                # Create begin tag
                begin = ET.SubElement(timeSpan, 'begin')
                begin.text = prevDateTime.strftime('%Y-%m-%dT%H:%M:%S')
                end = ET.SubElement(timeSpan, 'end')
                end.text = dateTime.strftime('%Y-%m-%dT%H:%M:%S')

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
            hrefElement.text = 'raster{0}.png'.format(index)

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

        return ET.tostring(kml), binaryPNGs

    def getAsGrassAsciiRaster(self, tableName, rasterId=1, rasterIdFieldName='id', rasterFieldName='raster',
                              newSRID=None, dataType=None):
        """
        Returns a string representation of the raster in GRASS ASCII raster format.
        """
        options = {}

        if dataType:
            if dataType not in self.GDAL_ASCII_DATA_TYPES:
                raise ValueError('"{}" is not a valid data type. Must be one of "{}"'.format(
                    dataType, '", "'.join(self.GDAL_ASCII_DATA_TYPES)))

            options = {'AAIGRID_DATATYPE': dataType}

        # Get raster in ArcInfo Grid format
        arcInfoGrid = self.getAsGdalRaster(rasterFieldName, tableName, rasterIdFieldName, rasterId, 'AAIGrid', newSRID,
                                           **options).splitlines()

        ## Convert arcInfoGrid to GRASS ASCII format ##
        # Get values from header which look something this:
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
        """
        Returns a string/buffer representation of the raster in the specified format. Wrapper for
        ST_AsGDALRaster function in the database.
        """

        # Check gdalFormat
        if not (gdalFormat in RasterConverter.supportedGdalRasterFormats(self._session)):
            raise ValueError('FORMAT NOT SUPPORTED: {0} format is not supported '
                             'in this PostGIS installation.'.format(gdalFormat))

        # Setup srid
        if newSRID:
            srid = ', {0}'.format(newSRID)
        else:
            srid = ''

        # Compile options
        if kwargs:
            optionsList = []
            for key, value in kwargs.items():
                kwargString = "'{0}={1}'".format(key, value)
                optionsList.append(kwargString)

            optionsString = ','.join(optionsList)
            options = ', ARRAY[{0}]'.format(optionsString)
        else:
            options = ''

        # Create statement
        statement = '''
                    SELECT ST_AsGDALRaster("{0}", '{1}'{5}{6})
                    FROM "{2}" WHERE "{3}"={4};
                    '''.format(rasterFieldName, gdalFormat, tableName, rasterIdFieldName, rasterId,  options, srid)

        # Execute query
        result = self._session.execute(statement).scalar()

        return bytes(result).decode('utf-8')

    @classmethod
    def supportedGdalRasterFormats(cls, sqlAlchemyEngineOrSession):
        """
        Return a list of the supported GDAL raster formats.
        """
        if isinstance(sqlAlchemyEngineOrSession, Engine):
            # Create sqlalchemy session
            sessionMaker = sessionmaker(bind=sqlAlchemyEngineOrSession)
            session = sessionMaker()
        elif isinstance(sqlAlchemyEngineOrSession, Session):
            session = sqlAlchemyEngineOrSession

        # Execute statement
        statement = 'SELECT * FROM st_gdaldrivers() ORDER BY short_name;'

        result = session.execute(statement)

        supported = dict()

        for row in result:
            supported[row[1]] = {'description': row[2], 'options': row[3]}

        return supported

    def setColorRamp(self, colorRamp=None):
        """
        Set the color ramp of the raster converter instance
        """
        if not colorRamp:
            self._colorRamp = RasterConverter.setDefaultColorRamp(ColorRampEnum.COLOR_RAMP_HUE)
        else:
            self._colorRamp = colorRamp

    def setDefaultColorRamp(self, colorRampEnum=ColorRampEnum.COLOR_RAMP_HUE):
        """
        Returns the color ramp as a list of RGB tuples
        """
        self._colorRamp = ColorRampGenerator.generateDefaultColorRamp(colorRampEnum)

    def setCustomColorRamp(self, colors=[], interpolatedPoints=10):
        """
        Accepts a list of RGB tuples and interpolates between them to create a custom color ramp.
        Returns the color ramp as a list of RGB tuples.
        """
        self._colorRamp = ColorRampGenerator.generateCustomColorRamp(colors, interpolatedPoints)

    def getMinMaxOfRasters(self, session, table, rasterIds, rasterField, rasterIdField, noDataValue):
        # Assemble rasters ids into string
        rasterIdsString = '({0})'.format(', '.join(rasterIds))
        for rasterId in rasterIds:
            statement = '''
                        UPDATE {1} SET {0} = ST_SetBandNoDataValue({0},1,{4})
                        WHERE {2} = {3};
                        '''.format(rasterField, table, rasterIdField, rasterId, noDataValue)

            session.execute(statement)

        # Get min and max for raster band 1
        statement = '''
                SELECT {2}, (stats).min, (stats).max
                FROM (
                SELECT {2}, ST_SummaryStats({0}, 1, true) As stats
                FROM {1}
                WHERE {2} IN {3}
                ) As foo;
                '''.format(rasterField, table, rasterIdField, rasterIdsString)
        result = session.execute(statement)
        # extract the stats
        minValues = []
        maxValues = []
        for row in result:
            if row.min is not None:
                minValues.append(row.min)
            if row.max is not None:
                maxValues.append(row.max)

        # In the case of no min or max values, assume 0 and 1, respectively
        try:
            minValue = min(minValues)
        except ValueError:
            minValue = 0
        try:
            maxValue = max(maxValues)
        except ValueError:
            maxValue = 1

        return minValue, maxValue

    def getRastersAsPngs(self, session, tableName, rasterIds, postGisRampString, rasterField='raster', rasterIdField='id',  cellSize=None, resampleMethod='NearestNeighbour'):
        """
        Return the raster in a PNG format
        """
        # Validate
        VALID_RESAMPLE_METHODS = ('NearestNeighbour', 'Bilinear', 'Cubic', 'CubicSpline', 'Lanczos')

        # Validate
        if resampleMethod not in VALID_RESAMPLE_METHODS:
            print('RASTER CONVERSION ERROR: {0} is not a valid resampleMethod.'
                  ' Please use either {1}'.format(resampleMethod,
                                                  ', '.join(VALID_RESAMPLE_METHODS)))

        if cellSize is not None:
            if not self.isNumber(cellSize):
                raise ValueError('RASTER CONVERSION ERROR: cellSize must be a number or None.')

        # Convert raster ids into formatted string
        rasterIdsString = '({0})'.format(', '.join(rasterIds))

        if cellSize is not None:
            statement = '''
                        SELECT ST_AsPNG(ST_Transform(ST_ColorMap(ST_Rescale({0}, {5}, '{6}'), 1, '{4}'), 4326, 'Bilinear')) As png
                        FROM {1}
                        WHERE {2} IN {3};
                        '''.format(rasterField, tableName, rasterIdField, rasterIdsString, postGisRampString, cellSize,
                                   resampleMethod)
        else:
            statement = '''
                        SELECT ST_AsPNG(ST_Transform(ST_ColorMap({0}, 1, '{4}'), 4326, 'Bilinear')) As png
                        FROM {1}
                        WHERE {2} IN {3};
                        '''.format(rasterField, tableName, rasterIdField, rasterIdsString, postGisRampString)
        result = session.execute(statement)
        return result

    def isNumber(self, value):
        """
        Validate whether a value is a number or not
        """
        try:
            str(value)
            float(value)
            return True

        except ValueError:
            return False
