"""
********************************************************************************
* Name: mapkit
* Author: Nathan Swain
* Created On: November 19, 2013
* Copyright: (c) Brigham Young University 2013
* License: BSD 2-Clause
********************************************************************************
"""
import logging
import requests
from sqlalchemy.ext.declarative import declarative_base
try:
    from sridentify import Sridentify
    sridentify_enabled = True
except ImportError:
    sridentify_enabled = False


Base = declarative_base()


log = logging.getLogger(__name__)


def version():
    return '1.2.6'


__version__ = version()


def lookupSpatialReferenceID(wellKnownText):
    """
    This function can be used to look up the EPSG spatial reference system using the web service available at:
    http://prj2epsg.org

    Args:
        wellKnownText (str): The Well Known Text definition of the spatial reference system.

    Returns:
        int: Spatial Reference ID or None if not found.
    """
    code = None

    try:
        # Optionally use epsg-ident - calls to local database
        if sridentify_enabled:
            ident = Sridentify(prj=wellKnownText, call_remote_api=False)
            code = ident.get_epsg()

        if not code:
            # Attempt to lookup using web service
            payload = {'mode': 'wkt',
                       'terms': wellKnownText}
            r = requests.get('http://prj2epsg.org/search.json', params=payload, timeout=10)

            if r.status_code == 200:
                json = r.json()

                for code in json['codes']:
                    code = code['code']

        if not code:
            log.warning("SRID Lookup Error: Spatial reference ID could not be identified.")

    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, RuntimeError):
        log.warning("SRID Lookup Error: Could not automatically determine spatial "
                    "reference ID, because there is no internet connection. "
                    "Please check connection and try again.")
    return code
