# -*- coding: utf-8 -*-
from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2
from vrptur_pois_data_extractor import *
import time

HOTEL_ID = 'hotel'


class Timer:

    def __init__(self):
        self.start = time.time()

    def done(self, unit=1000):
        end = time.time()
        total = end - self.start
        return total * unit


class CreateMeasurementCallback(object):
    """Create callback to calculate distances and duration between points."""

    def __init__(self, pois, measurement):
        """Initialize measurement dictionary."""
        size = len(pois)
        self.matrix = {}

        for from_node in range(size):
            self.matrix[from_node] = {}
            from_id = oid(pois[from_node])
            for to_node in range(size):
                to_id = oid(pois[to_node])
                self.matrix[from_node][to_node] = measurement[from_id][to_id]

    def distance(self, from_node, to_node):
        return self.matrix[from_node][to_node][0]

    def duration(self, from_node, to_node):
        return self.matrix[from_node][to_node][1]


class Tour(object):
    """
    Store a list of trips
    """

    def __init__(self, days):
        self.days = days
        self.trips = []
        self.duration = 0

    def distance(self):
        sum = 0
        for t in self.trips:
            sum += t.duration
        return sum


class Trip(object):
    """
    Store an day trip.
    Is an sequence of PoIs that construct the trip.
    Contains information about duration and time of trip.
    """

    def __init__(self, day):
        self.day = day
        self.pois = []
        self.duration = 0
        self.distance = 0

    def add_poi(self, poi):
        self.pois.append(poi)

    def add_duration(self, duration):
        self.duration += duration

    def add_distance(self, distance):
        self.distance += distance

    def print(self):
        print("[Trip for day " + str(self.day) + " ]")
        print("Duration: %.2f min" % self.duration)
        print("Distance: %.2f km" % self.distance)
        print("Sequence: " + " -> ".join([p["label"] for p in self.pois]))


def print_pois(pois):
    print("PoIs:")
    print("name (lat,lng)")
    for p in pois:
        print("%s (%f,%f)" % (p["label"], p["coordinates"][1], p["coordinates"][0]))
    print("\n")


def run_vrptur(pois, measurement, num_days):

    depot = 0  # The depot is the start and end point of each route.
    num_pois = len(pois)

    tour = Tour(num_days)

    # Create routing model.
    if num_pois > 0:
        routing = pywrapcp.RoutingModel(num_pois, num_days, depot)
        search_parameters = pywrapcp.RoutingModel.DefaultSearchParameters()

        # Setting first solution heuristic: the
        # method for finding a first solution to the problem.
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

        # search_parameters.first_solution_strategy = (
        #     routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)

        # The 'PATH_CHEAPEST_ARC' method does the following:
        # Starting from a route "start" node, connect it to the node which produces the
        # cheapest route segment, then extend the route by iterating on the last
        # node added to the route.

        # Put a callback to the measurement function here. The callback takes two
        # arguments (the from and to node indices) and returns the duration between
        # these nodes.

        measurement_between_pois = CreateMeasurementCallback(pois, measurement)
        duration_callback = measurement_between_pois.duration
        distance_callback = measurement_between_pois.distance
        routing.SetArcCostEvaluatorOfAllVehicles(duration_callback)

        # Add a dimension for duration.
        max_day_duration = 480  # in minutes
        fix_start_cumul_to_zero = True
        duration = "Duration"
        routing.AddDimension(
            duration_callback,
            max_day_duration,
            max_day_duration,
            fix_start_cumul_to_zero,
            duration
        )

        # Solve, displays a solution if any.
        assignment = routing.SolveWithParameters(search_parameters)
        if assignment:

            # Solution cost.
            tour.duration = assignment.ObjectiveValue()

            for day_nbr in range(num_days):

                trip = Trip(day_nbr)

                # Start: nodes 0 and 1
                index = routing.Start(day_nbr)
                index_next = assignment.Value(routing.NextVar(index))

                while not routing.IsEnd(index_next):

                    # Get indexes of nodes
                    node_index = routing.IndexToNode(index)
                    node_index_next = routing.IndexToNode(index_next)

                    # Increment trip
                    trip.add_poi(pois[node_index])
                    trip.add_duration(duration_callback(node_index, node_index_next))
                    trip.add_distance(distance_callback(node_index, node_index_next))

                    # Get next nodes
                    index = index_next
                    index_next = assignment.Value(routing.NextVar(index))

                # Get indexes of last nodes: (n-2) and (n-1)
                node_index = routing.IndexToNode(index)
                node_index_next = routing.IndexToNode(index_next)

                # Increment trip with last indexes
                trip.add_poi(pois[node_index])
                trip.add_poi(pois[node_index_next])
                trip.add_duration(duration_callback(node_index, node_index_next))
                trip.add_distance(distance_callback(node_index, node_index_next))

                tour.trips.append(trip)

        else:
            print('No solution found for num_days = ' + str(num_days))
    else:
        print('Specify an instance (PoIs) greater than 0.')

    return tour


def main():

    all_exec_time = Timer()

    # Create the data.
    load_data_time = Timer()
    pois, measurement = create_data_array()
    print_pois(pois)
    print("Load data time: %.2f ms\n" % load_data_time.done())

    days_range = [2, 3, 4, 5]  # [1, 2, 3, 4, 5]
    hotels = create_hotels()
    run_time = Timer()

    for num_days in days_range:
        for hotel in hotels:
            print("\n[[hotel = " + str(hotel["label"]) + ", num_days = " + str(num_days) + "]]")
            t_pois, t_measurement = set_hotel(hotel, pois, measurement)
            instance_time = Timer()
            tour = run_vrptur(t_pois, t_measurement, num_days)
            print("Computing time: %.2f ms" % instance_time.done())
            print("Duration: %.2f min" % tour.duration)
            print("Distance: %.2f km" % tour.distance())
            print("Trips:")
            for t in tour.trips:
                t.print()

    print("Execution time: %.2f ms" % run_time.done())
    print("\nTotal time (load + execution): %.2f ms\n" % all_exec_time.done())


def create_hotels():
    return [
        make_skinny_poi(
            _id=HOTEL_ID,
            name="Carmel Magna Praia Hotel",
            address="Av. Historiador Raimundo Girão, 1002 - Praia de Iracema, Fortaleza - CE, 60165-050",
            lat=-3.7230898,
            lng=-38.5066241
        ),
        make_skinny_poi(
            _id=HOTEL_ID,
            name="Hotel Gran Marquise",
            address="Av. Beira Mar, 3980 - Mucuripe, Fortaleza - CE, 60165-121",
            lat=-3.7233061,
            lng=-38.4853425
        ),
        make_skinny_poi(
            _id=HOTEL_ID,
            name="Crocobeach Hotel",
            address="Av. Clóvis Arrais Maia, 3700 - Antonio Diogo, Fortaleza - CE, 60183-694",
            lat=-3.736874,
            lng=-38.454724
        ),
        make_skinny_poi(
            _id=HOTEL_ID,
            name="Gran Mareiro Hotel",
            address="Rua Oswaldo Araújo, 100 - De Lourdes, Fortaleza - CE, 60177-325",
            lat=-3.740008,
            lng=-38.454015
        ),
        make_skinny_poi(
            _id=HOTEL_ID,
            name="Hotel Sonata De Iracema",
            address="Av. Beira Mar, 848 - Praia de Iracema, Fortaleza - CE, 60060-610",
            lat=-3.720099,
            lng=-38.512283
        )
    ]


def set_hotel(hotel, pois, measurement):

    copy_pois = pois[:]
    copy_measurement = dict(measurement)

    # Update all pois to include hotel measure
    hotel_dict = dict()
    hotel_dict[HOTEL_ID] = [0, 0]
    for poi in copy_pois:
        poi_id = oid(poi)
        m = measure(poi, hotel)
        copy_measurement[poi_id][HOTEL_ID] = m
        hotel_dict[poi_id] = m

    # Update pois array and measurement dictionary to include hotel
    copy_pois.insert(0, hotel)
    copy_measurement[HOTEL_ID] = hotel_dict

    return [copy_pois, copy_measurement]


def create_data_array():
    return extract_from_file("../../data/5967c27e8500002b1af50675-test.json")


if __name__ == '__main__':
    main()
