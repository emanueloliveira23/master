# -*- coding: utf-8 -*-

# P/ VRP:
# - Não há restrição de capacidade
# - Adicionar dimensão de tempo (restrição temporal)

from ortools.constraint_solver import pywrapcp
from ortools.constraint_solver import routing_enums_pb2
from vrptur_pois_data_extractor import *


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


def main():
    # Create the data.
    pois, measurement = create_data_array()
    num_pois = len(pois)
    depot = 0  # The depot is the start and end point of each route.
    num_days = 2

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
            # Display solution.
            # Solution cost.
            print("Total duration of all routes: " + str(assignment.ObjectiveValue()) + "\n")

            for day_nbr in range(num_days):
                index = routing.Start(day_nbr)
                index_next = assignment.Value(routing.NextVar(index))

                route = ''
                route_duration = 0

                while not routing.IsEnd(index_next):
                    node_index = routing.IndexToNode(index)
                    node_index_next = routing.IndexToNode(index_next)

                    route += pois[node_index]["label"] + " -> "
                    route_duration += duration_callback(node_index, node_index_next)

                    index = index_next
                    index_next = assignment.Value(routing.NextVar(index))

                node_index = routing.IndexToNode(index)
                node_index_next = routing.IndexToNode(index_next)

                route += pois[node_index]["label"] + " -> " + pois[node_index_next]["label"]
                route_duration += duration_callback(node_index, node_index_next)

                print("Route for day " + str(day_nbr) + ":\n\n" + route + "\n")
                print("Duration of route " + str(day_nbr) + ": " + str(route_duration))

        else:
            print('No solution found.')
    else:
        print('Specify an instance greater than 0.')


def create_data_array():

    pois, measurement = extract_from_file("../../data/5967c27e8500002b1af50675-test.json")

    hotel_id = "hotel"

    # Making depot/hotel like a PoI
    hotel = make_skinny_poi(
        _id=hotel_id,
        name="Praia Centro Hotel",
        address="Av. Monsenhor Tabosa, 740 - Praia de Iracema, Fortaleza - CE, 60165-010",
        lat=-3.7241911,
        lng=-38.5146956
    )

    # Update all pois to include hotel measure
    hotel_dict = dict()
    hotel_dict[hotel_id] = [0, 0]
    for poi in pois:
        pid = oid(poi)
        m = measure(poi, hotel)
        measurement[pid][hotel_id] = m
        hotel_dict[pid] = m

    # Update pois array and measurement dictionary to include hotel
    pois.insert(0, hotel)
    measurement[hotel_id] = hotel_dict

    return [pois, measurement]


if __name__ == '__main__':
    main()
