'''
********************************************************************************
* Name: mapkit.types
* Author: Nathan Swain
* Created On: January 2, 2014
* Copyright: (c) Brigham Young University 2013
* License: BSD 2-Clause
********************************************************************************
'''

import sqlalchemy.types as types


class Raster(types.UserDefinedType):
    '''
    Raster Column Type for SQLAlchemy
    '''
    def __init__(self):
        '''
        Constructor
        '''

    def get_col_spec(self):
        return 'raster'


class Geometry(types.UserDefinedType):
    '''
    Geometry Column Type for SQLAlchemy
    '''
    def __init__(self):
        '''
        Constructor
        '''

    def get_col_spec(self):
        return 'geometry'
