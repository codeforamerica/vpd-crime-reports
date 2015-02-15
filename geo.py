import math

EARTH_RADIUS = 6367000.  # mean Earth radius in meters
EARTH_CIRCUMFERENCE = math.pi * 2 * EARTH_RADIUS

def haversine(coords1, coords2):
    """
    Calculates the distance between two gps coordinates using the Haversine forumla
    See http://en.wikipedia.org/wiki/Haversine_formula for reference
    """

    lat1, lon1, lat2, lon2 = map(math.radians, [coords1[0], coords1[1], coords2[0], coords2[1]])

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2.) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.) ** 2
    c = 2 * math.asin(math.sqrt(a))
    dist = EARTH_RADIUS * c

    return dist
