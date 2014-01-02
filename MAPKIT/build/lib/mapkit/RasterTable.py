'''
********************************************************************************
* Name: RasterTable
* Author: Nathan Swain
* Created On: January 2, 2014
* Copyright: (c) Brigham Young University 2013
* License: BSD 2-Clause
********************************************************************************
'''

from mapkit import Base
from sqlatypes import Raster
from sqlalchemy import Column, Integer, String, DateTime

class RasterTable(Base):
    '''
    SQLAlchemy model for a raster table
    '''
    __tablename__ = 'rasters'
    
    id = Column(Integer, primary_key=True)
    filename = Column(String)
    timestamp = Column(DateTime)
    raster = Column(Raster)
    
    def __repr__(self):
        return '<RasterTable(filename={0}, timestamp={1}, raster={2}>'.format(self.filename,
                                                                              self.timestamp,
                                                                              self.raster)

        