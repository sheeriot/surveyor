from pluscodes import PlusCode
# from icecream import ic


def pluscode2latlon(pluscode):
    """
    This function takes a pluscode and returns the lat/lon of the center of the pluscode.
    """
    area = PlusCode(pluscode).area
    lat = round((area.sw.lat + area.ne.lat) / 2, 5)
    long = round((area.sw.lon + area.ne.lon) / 2, 5)
    return lat, long
