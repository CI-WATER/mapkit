"""
********************************************************************************
* Name: RasterLoader
* Author: Nathan Swain
* Created On: July 21, 2014
* Copyright: (c) Brigham Young University 2013
* License: BSD 2-Clause
********************************************************************************
"""

import math
import xml.etree.ElementTree as ET

from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
from sqlalchemy.orm.session import Session


class GeometryConverter(object):
    """
    An instance of GeometryConverter can be used to extract PostGIS
    geometry layers from a database and convert them into different formats
    for visualization.
    """

    def __init__(self, sqlAlchemyEngineOrSession):
        """
        Constructor
        """
        # Create sqlalchemy session
        if isinstance(sqlAlchemyEngineOrSession, Engine):
            sessionMaker = sessionmaker(bind=sqlAlchemyEngineOrSession)
            self._session = sessionMaker()
        elif isinstance(sqlAlchemyEngineOrSession, Session):
            self._session = sqlAlchemyEngineOrSession

    def getPointAsKmlCircle(self, tableName, radius, slices=25, extrude=0, zScaleFactor=1.0, geometryId=1,
                            geometryIdFieldName='id', geometryFieldName='geometry'):
        """
        Return a string representing a circular polygon in KML format with center at the coordinates of the point
        and radius as specified.
        """
        # Validate

        # Circle Params
        PI2 = 2 * math.pi

        # Get coordinates
        statement = '''
                    SELECT ST_X(ST_Transform({0}, 4326)) as x, ST_Y(ST_Transform({0}, 4326)) as y, ST_Z(ST_Transform({0}, 4326)) as z
                    FROM {1}
                    WHERE {2}={3};
                    '''.format(geometryFieldName, tableName, geometryIdFieldName, geometryId)

        result = self._session.execute(statement)

        centerLatitude= 0.0
        centerLongitude = 0.0

        for row in result:
            centerLatitude = row.x
            centerLongitude = row.y

        # Create circle coordinates
        coordinatesString = ''

        for i in range(slices):
            latitude = centerLatitude + (radius * math.cos(float(i) / float(slices) * PI2))
            longitude = centerLongitude + (radius * math.sin(float(i) / float(slices) * PI2))
            elevation = 0.0

            if extrude and zScaleFactor:
                elevation = extrude * zScaleFactor

            coordinatesString += '{0},{1},{2} '.format(latitude, longitude, elevation)

        # Create polygon element
        polygon = ET.Element('Polygon')

        # Create options elements
        tesselate = ET.SubElement(polygon, 'tesselate')
        tesselate.text = '1'

        extrudeElement = ET.SubElement(polygon, 'extrude')

        if extrude > 0:
            extrudeElement.text = '1'
        else:
            extrudeElement.text = '0'

        altitudeMode = ET.SubElement(polygon, 'altitudeMode')

        if extrude > 0:
            altitudeMode.text = 'relativeToGround'
        else:
            altitudeMode.text = 'clampToGround'

        # Geometry
        outerBoundaryIs = ET.SubElement(polygon, 'outerBoundaryIs')
        lindarRing = ET.SubElement(outerBoundaryIs, 'LinearRing')
        coordinates = ET.SubElement(lindarRing, 'coordinates')
        coordinates.text = coordinatesString.strip()

        return ET.tostring(polygon)
