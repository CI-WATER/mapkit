'''
********************************************************************************
* Name: RasterLoader
* Author: Nathan Swain
* Created On: December 17, 2013
* Copyright: (c) Brigham Young University 2013
* License: BSD 2-Clause
********************************************************************************
'''

import subprocess
import os
import json

from MapKitRaster import MapKitRaster
from mapkit import Base

from sqlalchemy.orm import sessionmaker

class RasterLoader(object):
    '''
    An instance of RasterLoader can be used to load rasters into a 
    PostGIS table with a raster field. If the table does not exist
    already, it will be created.
    '''


    def __init__(self, engine, raster2pgsql=''):
        '''
        Constructor
        '''
        self._engine = engine
        self._raster2pgsql = raster2pgsql

    def load(self, tableName='rasters', rasters=[]):
        '''
        Accepts a list of paths to raster files to load into the database.
        Returns the ids of the rasters loaded successfully in the same order
        as the list passed in.
        '''
        # Create table if necessary
        Base.metadata.create_all(self._engine)
            
        # Create a session
        Session = sessionmaker(bind=self._engine)
        session = Session()
        
        for raster in rasters:
            # Must read in using the raster2pgsql commandline tool.
            rasterPath = raster['path']

            if 'srid' in raster:
                srid = str(raster['srid'])
            else:
                srid = '4326'
                
            if 'no-data' in raster:
                noData = str(raster['no-data'])
            else:
                noData = '-1'
                                
            wellKnownBinary = RasterLoader.rasterToWKB(rasterPath, srid, noData, self._raster2pgsql)
                
            rasterBinary = wellKnownBinary
            
            # Get the filename
            filename = os.path.split(rasterPath)[1]

            # Populate raster record
            mapKitRaster = MapKitRaster()
            mapKitRaster.filename = filename
            mapKitRaster.raster = rasterBinary
            
            if 'timestamp' in raster:
                mapKitRaster.timestamp = raster['timestamp']
            
            # Add to session
            session.add(mapKitRaster)
        
        session.commit()
            
    @classmethod
    def rasterToWKB(cls, rasterPath, srid, noData, raster2pgsql):
        """
        Accepts a raster file and converts it to Well Known Binary text using the raster2pgsql
        executable that comes with PostGIS. This is the format that rasters are stored in a
        PostGIS database.
        """
        raster2pgsqlProcess = subprocess.Popen([raster2pgsql,
                                                '-s', srid, 
                                                '-N', noData, 
                                                rasterPath, 
                                                'n_a'],stdout=subprocess.PIPE)
        
        # This commandline tool generates the SQL to load the raster into the database
        # However, we want to use SQLAlchemy to load the values into the database.
        # We do this by extracting the value from the sql that is generated.
        sql, error = raster2pgsqlProcess.communicate()
        if sql:
            # This esoteric line is used to extract only the value of the raster (which is stored as a Well Know Binary string)
            # Example of Output:
            # BEGIN;
            # INSERT INTO "idx_index_maps" ("rast") VALUES ('0100...56C096CE87'::raster);
            # END;
            # The WKB is wrapped in single quotes. Splitting on single quotes isolates it as the
            # second item in the resulting list.
            wellKnownBinary = sql.split("'")[1]
        else:
            print error
            raise
        return wellKnownBinary

    @classmethod
    def makeSingleBandWKBRaster(cls, session, width, height, upperLeftX, upperLeftY, cellSizeX, cellSizeY, skewX, skewY, srid, dataArray, initialValue=None, noDataValue=None):
        """
        Generate Well Known Binary via SQL. Must be used on a PostGIS database as it relies on several PostGIS
        database functions.
        :param session: SQLAlchemy session object bound to a PostGIS enabled database
        :param height: Height of the raster (or number of rows)
        :param width: Width of the raster (or number of columns)
        :param upperLeftX: Raster upper left corner X coordinate
        :param upperLeftY: Raster upper left corner Y coordinate
        :param cellSizeX: Raster cell size in X direction
        :param cellSizeY: Raster cell size in Y direction
        :param skewX: Skew in X direction
        :param skewY: Skew in Y direction
        :param srid: SRID of the raster
        :param initialValue: Initial / default value of the raster cells
        :param noDataValue: Value of cells to be considered as cells containing no cells
        :param dataArray: 2-dimensional list of values or a string representation of a 2-dimensional list that will be used to populate the raster values
        """
        # Stringify the data array
        if isinstance(dataArray, str):
            dataArrayString = dataArray
        else:
            dataArrayString = json.dumps(dataArray)

        # Validate
        if initialValue is None:
            initialValue = 'NULL'

        if noDataValue is None:
            noDataValue = 'NULL'

        # Create the SQL statement
        statement = '''
                    SELECT ST_SetValues(
                        ST_AddBand(
                            ST_MakeEmptyRaster({0}::integer, {1}::integer, {2}::float8, {3}::float8, {4}::float8, {5}::float8, {6}::float8, {7}::float8, {8}::integer),
                            1::integer, '32BF'::text, {9}::double precision, {10}::double precision
                        ),
                        1, 1, 1, ARRAY{11}::double precision[][]
                    );
                    '''.format(width,
                               height,
                               upperLeftX,
                               upperLeftY,
                               cellSizeX,
                               cellSizeY,
                               skewX,
                               skewY,
                               srid,
                               initialValue,
                               noDataValue,
                               dataArrayString)

        result = session.execute(statement)

        # Extract result
        wellKnownBinary = ''

        for row in result:
            wellKnownBinary = row[0]

        return wellKnownBinary