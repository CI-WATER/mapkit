"""
********************************************************************************
* Name: mapkit
* Author: Nathan Swain
* Created On: November 19, 2013
* Copyright: (c) Brigham Young University 2013
* License: BSD 2-Clause
********************************************************************************
"""

import requests

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

def version():
    return '1.2.2'

__version__ = version()

def lookupSpatialReferenceID(wellKnownText):
    """
    This function can be used to look up the EPSG spatial reference system using the web service available at:
    http://prj2epsg.org

    Args:
        wellKnownText (str): The Well Known Text definition of the spatial reference system.

    Returns:
        int: Spatial Reference ID
    """
    payload = {'mode': 'wkt',
               'terms': wellKnownText}

    try:
        r = requests.get('http://prj2epsg.org/search.json', params=payload)
    except requests.exceptions.ConnectionError:
        print("SRID Lookup Error: Could not automatically determine spatial "
              "reference ID, because there is no internet connection. "
              "Please check connection and try again.")
        exit(1)

    if r.status_code == 200:
        json = r.json()

        for code in json['codes']:
            return code['code']
