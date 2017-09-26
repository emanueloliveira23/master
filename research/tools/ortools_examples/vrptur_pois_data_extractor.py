# -*- coding: utf-8 -*-

import json
from haversine import haversine
from math import radians, sin, sqrt, atan2

EARTH_RADIUS = 6371

TRANSPORT_MODES = {
    # In kilometers by hour (km/h). From: https://pt.wikipedia.org/wiki/Quil%C3%B4metro_por_hora
    'walk': 6,
    'bicycle': 25,
    'car': 50,
    'carInHighway': 85,
    'bus': 50,
    'busInHighway': 85
}

MAX_WALK_DISTANCE = 2  # Kilometers
MAX_URBAN_DISTANCE = 20  # Kilometers. Use to switch between highway or urban speed.
MINUTES_PER_HOUR = 60

DEFAULT_VISITING_TIME = 30  # in minutes


def oid(pi):
    return pi["_id"]["$oid"]


def is_equals(pi, pj):
    return oid(pi) == oid(pj)


def make_skinny_poi(_id, name, address, lat, lng):
    return {
        "_id": {
            "$oid": _id,
        },
        "label": name,
        "location": {
            "address": address,
        },
        "coordinates": [lng, lat]
    };


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


def distance(pi, pj, smart=False, default_distance=haversine_distance):
    """
    Compute the distance between two PoIs.
    If smart is on, the distance is measured base on the follow scenarios:
        - If the two PoIs are in same avenue, the Euclidean-haversine distance is used.
        - If the two PoIs aren't in the same avenue, the Manhattan-haversine distance is used.
    :param pi: A poi of interest with "coordinates" attribute.
    :param pj: A poi of interest with "coordinates" attribute.
    :param smart: Flag that turn on the detection of best fit distance measure.
    :param default_distance: Distance measure used if smart is off.
    :return: The distance in kilometers between two points of interests (PoI).
    """

    pi_lng, pi_lat = pi["coordinates"]
    pj_lng, pj_lat = pj["coordinates"]

    if smart:
        if in_same_avenue(pi, pj):
            d = haversine_distance(pi_lng, pi_lat, pj_lng, pj_lat)
        else:
            d = manhattan_distance(pi_lng, pi_lat, pj_lng, pj_lat)
    else:
        d = default_distance(pi_lng, pi_lat, pj_lng, pj_lat)

    return d


def duration(pi, pj, mode="auto", auto_threshold=MAX_WALK_DISTANCE, max_urban_threshold=MAX_URBAN_DISTANCE):
    """
    Compute the duration between two PoIs in minutes.
    :param pi: A poi origin of interest with "coordinates" attribute.
    :param pj: A poi target of interest with "coordinates" attribute.
    :param mode: A transport mode.
    :param auto_threshold: If mode == "auto", this threshold is used to decide if mode is walk or car.
    :param max_urban_threshold: If mode === "auto", this threshold is used to decide if mode is car or car in highway.
    :return: The travel duration between pi to pj using such transport mode.
    """

    dist = distance(pi, pj)

    if dist == 0:
        return 0

    if mode == "auto":
        if dist <= auto_threshold:
            if dist <= max_urban_threshold:
                mode = "car"
            else:
                mode = "carInHighway"
        else:
            mode = "walk"

    speed = TRANSPORT_MODES[mode]

    pi_visiting_time = pi.get("visitingTime", DEFAULT_VISITING_TIME)
    pj_visiting_time = pj.get("visitingTime", DEFAULT_VISITING_TIME)

    travel_time = (dist / speed) * MINUTES_PER_HOUR

    return travel_time + pi_visiting_time / 2 + pj_visiting_time / 2


def measure(source, target):
    return [distance(source, target), duration(source, target)]


def measure_all(source, pois_target):
    source_dict = {}
    for target in pois_target:
        if not is_equals(source, target):
            source_dict[oid(target)] = measure(source, target)
        else:
            source_dict[oid(target)] = [0, 0]
    return source_dict


def extract_from_list(pois):
    """
    - Take an array of PoIs.
    - Each json object contains data about an PoI.
    - Extract the distance between all PoIs.
    - The distance metric used is conditional:
        - If two PoIs are in the same avenue/street (if this info is available), use haversine distance.
        - If two PoIs aren't in the same avenue/street, use Manhattan Distance for two geolocations.

    :param pois: An array of PoIs
    :return: a array following the above pattern:
        [
            [
                { /* poi object */ },
                { /* poi object */ }
                ...
            ],
            {
                poi1_Id: {
                    poi2_Id: [distance, duration],
                    poi3_Id: [distance, duration],
                    ...
                },
                poi2_Id: {
                    poi1_Id: [distance, duration],
                    poi3_Id: [distance, duration],
                    ...
                }
                ...
            }
        ]
    """

    # Make measurement dictionary
    measurement = {}
    for pi in pois:
        measurement[oid(pi)] = measure_all(pi, pois)

    return [pois, measurement]


def extract_from_file(pois_file):
    """
    - Each json object contains data about an PoI.
    - Extract the distance between all PoIs.
    - The distance metric used is conditional:
        - If two PoIs are in the same avenue/street (if this info is available), use haversine distance.
        - If two PoIs aren't in the same avenue/street, use Manhattan Distance for two geolocations.

    :param pois_file: File which contains a json object per line.
    :return: a big dictionary following the above pattern:
        [
            [
                { /* poi object */ },
                { /* poi object */ }
                ...
            ],
            {
                poi1_Id: {
                    poi2_Id: [distance, duration],
                    poi3_Id: [distance, duration],
                    ...
                },
                poi2_Id: {
                    poi1_Id: [distance, duration],
                    poi3_Id: [distance, duration],
                    ...
                }
                ...
            }
        ]
    """

    # Extract all pois and put into array
    pois = []
    with open(pois_file, encoding='utf-8') as fd:
        for line in fd:
            pois.append(json.loads(line))

    return extract_from_list(pois)
