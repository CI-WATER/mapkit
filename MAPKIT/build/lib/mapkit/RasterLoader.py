'''
********************************************************************************
* Name: RasterLoader
* Author: Nathan Swain
* Created On: December 17, 2013
* Copyright: (c) Brigham Young University 2013
* License: BSD 2-Clause
********************************************************************************
'''

import subprocess, os, datetime

from RasterTable import RasterTable
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
                                
            raster2pgsqlProcess = subprocess.Popen(
                                                   [
                                                    self._raster2pgsql,
                                                    '-s',
                                                    srid,
                                                    '-N',
                                                    noData,
                                                    rasterPath, 
                                                    'n_a'
                                                   ],
                                                   stdout=subprocess.PIPE
                                                  )
            
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
                wellKnownBinary =  sql.split("'")[1]
                
            else:
                print error
                raise
                
            rasterBinary = wellKnownBinary
            
            # Get the filename
            filename = os.path.split(rasterPath)[1]
            
#             # Construct statement
#             if 'timestamp' in raster:
#                 timestamp = raster['timestamp']
#                 
#                 statement = '''
#                             BEGIN;
#                             CREATE TABLE IF NOT EXISTS "{0}" ("id" serial PRIMARY KEY, "raster" raster,"filename" text, "timestamp" timestamp);
#                             INSERT INTO "{0}" ("raster","filename","timestamp") VALUES ('{1}'::raster,'{2}','{3}') RETURNING "id";
#                             END;
#                             '''.format(tableName, rasterBinary, filename, timestamp)
#             else:
#                 statement = '''
#                             BEGIN;
#                             CREATE TABLE IF NOT EXISTS "{0}" ("id" serial PRIMARY KEY, "raster" raster,"filename" text, "timestamp" timestamp);
#                             INSERT INTO "{0}" ("raster","filename") VALUES ('{1}'::raster,'{2}') RETURNING "id";
#                             END;
#                             '''.format(tableName, rasterBinary, filename)
#                         
#             result = self._session.execute(statement)

            
            Base.metadata.create_all(self._engine)
            
            Session = sessionmaker(bind=self._engine)
            session = Session()

            raster = RasterTable()
            raster.filename = filename
            raster.raster = rasterBinary
            session.add(raster)
            session.commit()
            
            
            
            
            
            
        
        
        