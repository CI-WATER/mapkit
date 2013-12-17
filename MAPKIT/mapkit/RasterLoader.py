'''
********************************************************************************
* Name: RasterLoader
* Author: Nathan Swain
* Created On: December 17, 2013
* Copyright: (c) Brigham Young University 2013
* License: BSD 2-Clause
********************************************************************************
'''

class RasterLoader(object):
    '''
    An instance of RasterLoader can be used to load rasters into a 
    PostGIS table with a raster field. If the table does not exist
    already, it will be created.
    '''


    def __init__(self):
        '''
        Constructor
        '''
        