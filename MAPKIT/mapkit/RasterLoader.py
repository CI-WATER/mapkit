'''
********************************************************************************
* Name: RasterLoader
* Author: Nathan Swain
* Created On: December 17, 2013
* Copyright: (c) Brigham Young University 2013
* License: BSD 2-Clause
********************************************************************************
'''

import subprocess, os

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
        '''
        Accepts a raster file and converts it to Well Known Binary text using the raster2pgsql
        executable that comes with PostGIS. This is the format that rasters are stored in a
        PostGIS database.
        '''
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
            
            
            
            
            
            
        
        
        