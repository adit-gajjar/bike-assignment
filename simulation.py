"""Assignment 1 - Simulation

=== CSC148 Fall 2017 ===
Diane Horton and David Liu
Department of Computer Science,
University of Toronto


=== Module Description ===

This file contains the Simulation class, which is the main class for your
bike-share simulation.

At the bottom of the file, there is a sample_simulation function that you
can use to try running the simulation at any time.
"""
import csv
from datetime import datetime, timedelta
import json
from typing import Dict, List, Tuple

from bikeshare import Ride, Station
from container import PriorityQueue
from visualizer import Visualizer

# Datetime format to parse the ride data
DATETIME_FORMAT = '%Y-%m-%d %H:%M'


class Simulation:
    """Runs the core of the simulation through time.

    === Attributes ===
    all_rides:
        A list of all the rides in this simulation.
        Note that not all rides might be used, depending on the timeframe
        when the simulation is run.
    all_stations:
        A dictionary containing all the stations in this simulation.
    visualizer:
        A helper class for visualizing the simulation.
    active_rides:
        A list of all active rides in the simulation meaning rides that have
        started and are inprogress. Rides are added and removed from the list
        as they various rides start and end.
    event_queue:
        Is a priority queue which stores ride events based off the times the
        events are initiated. Events are added and removed as new events in
        the simulation occur.

    """
    all_stations: Dict[str, Station]
    all_rides: List[Ride]
    visualizer: Visualizer
    active_rides: List[Ride]
    event_queue: PriorityQueue

    def __init__(self, station_file: str, ride_file: str) -> None:
        """Initialize this simulation with the given configuration settings.
        """
        self.visualizer = Visualizer()
        self.all_stations = create_stations(station_file)
        self.all_rides = create_rides(ride_file, self.all_stations)
        self.active_rides = []
        self.event_queue = PriorityQueue()

    def run(self, start: datetime, end: datetime) -> None:
        """Run the simulation from <start> to <end>.
        """
        step = timedelta(minutes=1)  # Each iteration spans one minute of time

        self.initialize_queue(start, end)

        while start != end:
            self._update_active_rides(start)
            self.update_simulation(start)  # updates graphics and statistics
            start += step
        while True:
            if self.visualizer.handle_window_events():
                return  # Stop the simulation

    def _update_active_rides(self, time: datetime) -> None:
        """Update this simulation's list of active rides for the given time.

        REQUIRED IMPLEMENTATION NOTES:
        -   Loop through `self.all_rides` and compare each Ride's start and
            end times with <time>.

            If <time> is between the ride's start and end times (inclusive),
            then add the ride to self.active_rides if it isn't already in
            that list.

            Otherwise, remove the ride from self.active_rides if it is in
            that list.

        -   This means that if a ride started before the simulation's time
            period but ends during or after the simulation's time period,
            it should still be added to self.active_rides.

        """
        for ride in self.all_rides:
            if ride.start_time == time:
                validated = validate_ride_start_event(ride)
                if validated:
                    self.active_rides.append(ride)
                else:  # if the station has no more bikes to employ remove it.
                    self.all_rides.remove(ride)

            if ride.end_time == time:
                self.active_rides.remove(ride)
                validate_ride_end_event(ride)

    def calculate_statistics(self) -> Dict[str, Tuple[str, float]]:
        """Return a dictionary containing statistics for this simulation.

        The returned dictionary has exactly four keys, corresponding
        to the four statistics tracked for each station:
          - 'max_start'
          - 'max_end'
          - 'max_time_low_availability'
          - 'max_time_low_unoccupied'

        The corresponding value of each key is a tuple of two elements,
        where the first element is the name (NOT id) of the station that has
        the maximum value of the quantity specified by that key,
        and the second element is the value of that quantity.

        For example, the value corresponding to key 'max_start' should be the
        name of the station with the most number of rides started at that
        station, and the number of rides that started at that station.
        """
        max_start = self.get_optimal_stat('ride_starts')
        max_end = self.get_optimal_stat('ride_finishes')
        max_time_low_availability = self.get_optimal_stat('low_availability')
        max_time_low_unoccupied = self.get_optimal_stat('low_unoccupied')

        return {
            'max_start': max_start,
            'max_end': max_end,
            'max_time_low_availability': max_time_low_availability,
            'max_time_low_unoccupied': max_time_low_unoccupied
        }

    def get_optimal_stat(self, stat: str) -> Tuple[str, int]:
        """ Takes in a stat which is a string that corresponds to a key for
         dictionary containing a stations statisitics and then finds the largest
         value for the inputed statistic.

         """
        max_value = -1
        max_station = None

        for station in self.all_stations.values():

            if station.stats[stat] > max_value:
                max_station = station.name
                max_value = station.stats[stat]
            elif station.stats[stat] == max_value:
                max_station = alpha_order(max_station, station.name)

        return (max_station, max_value)

    def _update_active_rides_fast(self, time: datetime) -> None:
        """Update this simulation's list of active rides for the given time.

        REQUIRED IMPLEMENTATION NOTES:
        -   see Task 5 of the assignment handout
        """
        if not self.event_queue.is_empty():
            curr = self.event_queue.remove()
            if curr.time == time:
                # Runs all events that occur at the current.
                self.process_events(curr, time)
            else:
                # the event doesnt match the time then put back in the queue
                self.event_queue.add(curr)

    def update_statistics(self) -> None:
        """
        Updates the statistics for stations in particular this function is
        responsile for updating the low_availability and low_unoccupancy
        statistics of all the stations every minute that goes by.
        """
        for station in self.all_stations.values():
            if station.num_bikes <= 5:
                station.stats['low_availability'] += 60
                # The station has at most 5 bikes available
            if station.capacity - station.num_bikes <= 5:
                station.stats['low_unoccupied'] += 60
                # the station has at most 5 unoccupied spots.

    def initialize_queue(self, start: datetime, end: datetime) -> None:
        """
        A helper function which initializes the event queue before the <start>
        time of the simulationby creating
        corresponding ride start events for all the valid rides.
        """
        lst = self.create_ride_start_events(self.all_rides, start, end)
        for event in lst:
            self.event_queue.add(event)

    def create_ride_start_events(self, rides_list: List['Ride'],
                                 sim_start: 'datetime',
                                 sim_end: 'datetime') -> List:
        """
        Goes through <rides_list> and generates a list of corresponding of
        ridestart events to be used by a priority queue. If the ride is already
        going on before the <sim_start> then the ride is added directly to
        active rides list.
        """
        all_ride_events = []
        for ride in rides_list:
            # generates and adds a ride start event if valid.
            if valid_ride(ride, sim_start, sim_end):
                if ride.start_time < sim_start and ride.end_time <= sim_end:
                    self.active_rides.append(ride)
                    end_event = RideEndEvent(self, ride.end_time, ride)
                    self.event_queue.add(end_event)
                else:
                    event = RideStartEvent(self, ride.start_time, ride)
                    all_ride_events.append(event)
        return all_ride_events

    def process_events(self, curr: 'Event',
                       time: 'datetime') -> None:
        """ Helper function which checks if multiple events need to be processed
            at the same time in the priority queue
        """
        while curr.time == time:
            generated_events = curr.process()
            if generated_events is not None:
                self.event_queue.add(generated_events[0])

            if not self.event_queue.is_empty():
                curr = self.event_queue.remove()
            else:
                break
        self.event_queue.add(curr)

    def update_simulation(self, time: 'datetime') -> None:
        """ Updates the simulation every minute and keeps it progressing
            by updating the the active rides as well as
            maintaining what is rendered.
        """
        self.update_statistics()
        self.visualizer.render_drawables(
            list(self.all_stations.values()) + self.active_rides, time)


def create_stations(stations_file: str) -> Dict[str, 'Station']:
    """Return the stations described in the given JSON data file.

    Each key in the returned dictionary is a station id,
    and each value is the corresponding Station object.
    Note that you need to call Station(...) to create these objects!

    Precondition: stations_file matches the format specified in the
                  assignment handout.

    This function should be called *before* _read_rides because the
    rides CSV file refers to station ids.
    """
    # Read in raw data using the json library.
    with open(stations_file) as file:
        raw_stations = json.load(file)

    stations = {}
    for s in raw_stations['stations']:
        # Extract the relevant fields from the raw station JSON.
        # s is a dictionary with the keys 'n', 's', 'la', 'lo', 'da', and 'ba'
        # as described in the assignment handout.
        # NOTE: all of the corresponding values are strings, and so you need
        # to convert some of them to numbers explicitly using int() or float().
        stations[s['n']] = Station((float(s['lo']), float(s['la'])),
                                   int(s['da']) + int(s['ba']),
                                   int(s['da']), s['s'])

    return stations


def create_rides(rides_file: str,
                 stations: Dict[str, 'Station']) -> List['Ride']:
    """Return the rides described in the given CSV file.

    Lookup the station ids contained in the rides file in <stations>
    to access the corresponding Station objects.

    Ignore any ride whose start or end station is not present in <stations>.

    Precondition: rides_file matches the format specified in the
                  assignment handout.
    """
    rides = []
    with open(rides_file) as file:
        for line in csv.reader(file):
            # line is a list of strings, following the format described
            # in the assignment handout.
            #
            # Convert between a string and a datetime object
            # using the function datetime.strptime and the DATETIME_FORMAT
            # constant we defined above. Example:
            # >>> datetime.strptime('2017-06-01 8:00', DATETIME_FORMAT)
            # datetime.datetime(2017, 6, 1, 8, 0)
            if line[1] in stations and line[3] in stations:
                r = Ride(stations[line[1]], stations[line[3]],
                         (datetime.strptime(line[0], DATETIME_FORMAT)\
                         , datetime.strptime(line[2], DATETIME_FORMAT)))
                if r.start_time < r.end_time:
                    rides.append(r)

    return rides


class Event:
    """An event in the bike share simulation.

    Events are ordered by their timestamp.
    === Attributes ===
    simulation: Is the simulation in which the event is to be processed
    time: Is a datetime object which stores the time the event occur in the
        simulation.
    """
    simulation: 'Simulation'
    time: datetime

    def __init__(self, simulation: 'Simulation', time: datetime) -> None:
        """Initialize a new event."""
        self.simulation = simulation
        self.time = time

    def __lt__(self, other: 'Event') -> bool:
        """Return whether this event is less than <other>.

        Events are ordered by their timestamp.
        """
        return self.time < other.time

    def process(self) -> List['Event']:
        """Process this event by updating the state of the simulation.

        Return a list of new events spawned by this event.
        """
        raise NotImplementedError


class RideStartEvent(Event):
    """An event corresponding to the start of a ride.
    === Attributes ===
    simulation: Is the simulation in which the event is to be processed
    time: Is a datetime object which stores the time the event occur in the
        simulation.
    ride: Is the ride object which corresponds to the event.
    """

    def __init__(self, simulation: 'Simulation', time: datetime, ride: 'Ride'):
        Event.__init__(self, simulation, time)
        self.ride = ride

    def process(self) -> List['Event']:
        """
        When a RideStartEvent is processed it checks if the ride_start is
        valid. If the ride is deemed to be valid and not an anomaly in the data
        it adds the ride to the active rides list, and generates a corresponding
        RideEndEvent which it returns in a list.
        """
        if validate_ride_start_event(self.ride):
            self.simulation.active_rides.append(self.ride)
            # Generate a RideEndEvent
            curr = self.ride
            end_event = RideEndEvent(self.simulation, curr.end_time, curr)
            generated_event = [end_event]
            return generated_event


class RideEndEvent(Event):
    """An event corresponding to the start of a ride.
        === Attributes ===
    simulation: Is the simulation in which the event is to be processed
    time: Is a datetime object which stores the time the event occur in the
        simulation.
    ride: Is the ride object which corresponds to the event.
    """
    def __init__(self, simulation: 'Simulation', time: datetime, ride: 'Ride'):
        Event.__init__(self, simulation, time)
        self.ride = ride

    def process(self) -> None:
        """
        When a rideEndEvent is processed no list of Events is return
        as a rideEndEvent does not generate any additional Events. All that the
        rideEndEvent does it remove the ride from the active rides list.
        """
        # Remove ride from the list
        validate_ride_end_event(self.ride)
        self.simulation.active_rides.remove(self.ride)


#  Helper functions


def validate_ride_start_event(ride: 'Ride') -> bool:
    """ Checks if the condition are valid to initiate a ride start event.
     function also updates the statistics accordingly.
    """
    valid = None
    start_station = ride.start
    if start_station.num_bikes > 0:
        start_station.stats['ride_starts'] += 1
        start_station.num_bikes -= 1
        valid = True
    else:
        valid = False
    return valid


def validate_ride_end_event(ride: 'Ride') -> bool:
    """ Function validate whether a <ride> can end at that station by
    that station, and updates that stations statistics accordingly.
    """
    end_station = ride.end
    valid = False
    # if there is space to park the bike then update stats
    if end_station.capacity - end_station.num_bikes > 0:
        end_station.num_bikes += 1
        end_station.stats['ride_finishes'] += 1
        valid = True
    else:
        valid = False
    return valid


def alpha_order(string1: str, string2: str) -> str:
    """
    Compares <string1>  and  <string2> then retuns the string
    which comes alphabetically before the other.
    >>> alpha_order('bmw', 'alfa')
    alfa
    """
    if string1 < string2:
        return string1
    else:
        return string2


def sample_simulation() -> Dict[str, Tuple[str, float]]:
    """Run a sample simulation. For testing purposes only."""
    sim = Simulation('stations.json', 'sample_rides.csv')

    sim.run(datetime(2017, 6, 1, 7, 0, 0),
            datetime(2017, 6, 1, 9, 0, 0))

    return sim.calculate_statistics()


def valid_ride(ride: 'Ride', sim_start: 'datetime',
               sim_end: 'datetime') -> bool:
    """ A helper function that determines whether a ride is an anomaly
        and return if it is <valid> or not.
    """
    valid = True
    if ride.start_time > sim_end or ride.start_time > ride.end_time:
        # if the ride starts after sim end dont add it or ends before it
        # starts
        valid = False
    elif ride.start_time < sim_start and ride.end_time <= sim_start:
        # if a ride starts and ends before the sim starts dont count it.
        valid = False
    elif ride.start_time < sim_start and ride.end_time > sim_end:
        valid = False
    elif ride.start_time > ride.end_time:
        # if a rides end time is before its start time.
        valid = False
    return valid


if __name__ == '__main__':
    print(sample_simulation())
