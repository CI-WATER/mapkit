'''
********************************************************************************
* Name: mapit
* Author: Nathan Swain
* Created On: November 19, 2013
* Copyright: (c) Brigham Young University 2013
* License: BSD 2-Clause
********************************************************************************
'''

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

def version():
    return '1.0.0'