# -*- coding: utf-8 -*-
"""
- Take a input file which contains a json object per line.
- Each json object contains data about an PoI.
- Extract the distance between all PoIs.
- The distance metric used is conditional:
    - If two PoIs are in the same avenue/street (if this info is available), use haversine distance.
    - If two PoIs aren't in the same avenue/street, use Manhattan Distance for two geolocations.
- The return is a big dictionary following the above pattern:

    {
        poi1_Id: {
            poi2_Id: distance,
            poi3_Id: distance,
            ...
        },
        poi2_Id: {
            poi1_Id: distance,
            poi3_Id: distance,
            ...
        }
        ...
    }

"""

import sys
import json
from haversine import haversine
from math import radians, sin, sqrt, atan2

EARTH_RADIUS = 6371


def oid(pi):
    return pi["_id"]["$oid"]


def is_equals(pi, pj):
    return oid(pi) == oid(pj)


def get_avenue(p):

    p_venue_data = p.get("foursquareVenue", False)

    if p_venue_data:
        address = p_venue_data.get("location", {}).get("address", "")
    else:
        address = p.get("location", {}).get("address", "")

    if not address == "":
        address = address.split(",")[0]
    else:
        address = False

    return address


def in_same_avenue(pi, pj):
    pi_avenue = get_avenue(pi)
    pj_avenue = get_avenue(pj)

    if pi_avenue and pj_avenue:
        same_avenue = str.lower(pi_avenue) == str.lower(pj_avenue)
    else:
        same_avenue = False

    return same_avenue


def haversine_distance(pi_lng, pi_lat, pj_lng, pj_lat):
    a = (pi_lat, pi_lng)
    b = (pj_lat, pj_lng)
    return haversine(a, b)


def manhattan_distance(pi_lng, pi_lat, pj_lng, pj_lat):

    # convert decimal degrees to radians
    r_pi_lat, r_pi_lng, r_pj_lat, r_pj_lng = map(radians, [pi_lat, pi_lng, pj_lat, pj_lng])

    # haversine formula for delta_lat
    dlat = r_pj_lat - r_pi_lat
    a = sin(dlat / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    lat_d = c * EARTH_RADIUS

    # haversine formula for delta_lon
    dlon = r_pj_lng - r_pi_lng
    a = sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    lon_d = c * EARTH_RADIUS

    return lat_d + lon_d


def distance(pi, pj):
    """
    Compute the distance between to PoIs
    If the two PoIs are in same avenue, the Euclidean-haversine distance is used.
    If the two PoIs aren't in the same avenue, the Manhattan-haversine distance is used.
    :param pi: A poi of interest with "coordinates" attribute.
    :param pj: A poi of interest with "coordinates" attribute.
    :return: The distance in kilometers between two points of interests (PoI).
    """
    pi_lng, pi_lat = pi["coordinates"]
    pj_lng, pj_lat = pj["coordinates"]

    if in_same_avenue(pi, pj):
        d = haversine_distance(pi_lng, pi_lat, pj_lng, pj_lat)
    else:
        d = manhattan_distance(pi_lng, pi_lat, pj_lng, pj_lat)
    return d


def get_distance_dictionary(file_dataset):

    # Extract all pois and put into array
    pois = []
    with open(file_dataset, encoding='utf-8') as fd:
        for line in fd:
            pois.append(json.loads(line))

    # Make dictionary distance
    distance_dictionary = {}
    for pi in pois:
        pi_dict = {}
        for pj in pois:
            if not is_equals(pi, pj):
                pi_dict[oid(pj)] = distance(pi, pj)
        distance_dictionary[oid(pi)] = pi_dict

    data = {
        pois: pois,
        distance_dictionary: distance_dictionary
    }

    return data


def main(argv):
    file_dataset = argv[1]
    distance_dictionary = get_distance_dictionary(file_dataset)
    print(distance_dictionary)


if __name__ == '__main__':
    main(sys.argv)

