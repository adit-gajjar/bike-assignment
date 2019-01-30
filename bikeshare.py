"""Assignment 1 - Bike-share objects

=== CSC148 Fall 2017 ===
Diane Horton and David Liu
Department of Computer Science,
University of Toronto


=== Module Description ===

This file contains the Station and Ride classes, which store the data for the
objects in this simulation.

There is also an abstract Drawable class that is the superclass for both
Station and Ride. It enables the simulation to visualize these objects in
a graphical window.
"""
from datetime import datetime
from typing import Tuple


# Sprite files
STATION_SPRITE = 'stationsprite.png'
RIDE_SPRITE = 'bikesprite.png'


class Drawable:
    """A base class for objects that the graphical renderer can be drawn.

    === Public Attributes ===
    sprite:
        The filename of the image to be drawn for this object.
    """
    sprite: str

    def __init__(self, sprite_file: str) -> None:
        """Initialize this drawable object with the given sprite file.
        """
        self.sprite = sprite_file

    def get_position(self, time: datetime) -> Tuple[float, float]:
        """Return the (lat, long) position of this object at the given time.
        """
        raise NotImplementedError


class Station(Drawable):
    """A Bixi station.

    === Public Attributes ===
    capacity:
        the total number of bikes the station can store
    location:
        the location of the station in lat/long coordinates
    name: str
        name of the station
    num_bikes: int
        current number of bikes at the station
    stats: dict
        A dictionary containing of all the stations stats which includes
        the number of ride starts and finishes as well as the amount of time
        the station was in a state of low availability or low unoccupancy
    === Representation Invariants ===
    - 0 <= num_bikes <= capacity
    - stats['ride_starts'] >= 0
    - stats['ride_finishes'] >= 0
    - stats['low_availability'] >= 0
    - stats['low_unoccupied'] >= 0

    """
    name: str
    location: Tuple[float, float]
    capacity: int
    num_bikes: int
    stats: dict

    def __init__(self, pos: Tuple[float, float], cap: int,
                 num_bikes: int, name: str) -> None:
        """Initialize a new station.

        Precondition: 0 <= num_bikes <= cap
        """
        Drawable.__init__(self, STATION_SPRITE)
        self.location = pos
        self.capacity = cap
        self.num_bikes = num_bikes
        self.name = name
        self.stats = {'ride_starts': 0, 'ride_finishes': 0,
                      'low_availability': 0,
                      'low_unoccupied': 0
                     }

    def get_position(self, time: datetime) -> Tuple[float, float]:
        """Return the (lat, long) position of this station for the given time.

        Note that the station's location does *not* change over time.
        The <time> parameter is included only because we should not change
        the header of an overridden method.
        """
        return self.location


class Ride(Drawable):
    """A ride using a Bixi bike.

    === Attributes ===
    start:
        the station where this ride starts
    end:
        the station where this ride ends
    start_time:
        the time this ride starts
    end_time:
        the time this ride ends
    speed:
        the amount of distance the ride travels in both x and y direactions
        to reach its destination at the correct time. can be both positive
        or negative based on the direction of travel.
    === Representation Invariants ===
    - start_time < end_time
    """
    start: Station
    end: Station
    start_time: datetime
    end_time: datetime
    speed: Tuple[float, float]

    def __init__(self, start: Station, end: Station,
                 times: Tuple[datetime, datetime]) -> None:
        """Initialize a ride object with the given start and end information.
        """
        super(Ride, self).__init__(RIDE_SPRITE)
        self.start, self.end = start, end
        self.start_time, self.end_time = times[0], times[1]
        self.speed = determine_speed(self.start, self.end, self.start_time,
                                     self.end_time)

    def get_position(self, time: datetime):
        """Return the position of this ride for the given time.

        A ride travels in a straight line between its start and end stations
        at a constant speed.
        """
        diff = (time - self.start_time).total_seconds() // 60
        move_x = self.speed[0] * diff
        move_y = self.speed[1] * diff
        init_position = self.start.get_position(datetime.now())

        return (init_position[0] + move_x, init_position[1] + move_y)

# Helper Functions


def determine_speed(start: Station, end: Station, start_time: datetime,
                    end_time: datetime) -> Tuple[float, float]:
    """
    determines the distance a ride will travel every minute to reach its
    destination and returns it as a tuple corresponding to (x,y) coordinates.
    delta time must be greater than 0 and not negative as it is used for
    division.
    === Representation Invariants ===
    delta_time > 0

    """
    delta_distance = get_start_end_position_delta(start, end)

    delta_time = get_time_delta_minutes(start_time, end_time)

    if delta_time == 0:  # delta time must never be 0.
        delta_time = 1
    # calculates speed using change in distance over time formula.
    speed_x = (delta_distance[0]) / delta_time
    speed_y = (delta_distance[1]) / delta_time
    return (speed_x, speed_y)


def get_start_end_position_delta(start_station: 'Station',
                                 end_station: 'Station') -> Tuple[float, float]:
    """
    A helper function that returns a tuple containing the difference in position
    between <start_station> and <end_station>
    """
    x1_distance = start_station.get_position(datetime.now())[0]
    x2_distance = end_station.get_position(datetime.now())[0]
    y1_distance = start_station.get_position(datetime.now())[1]
    y2_distance = end_station.get_position(datetime.now())[1]

    return (x2_distance - x1_distance, y2_distance - y1_distance)


def get_time_delta_minutes(start_time: datetime, end_time: datetime) -> int:
    """
    determines the difference in time in minutes between 2 given
    datetime objects <start_time> and <end_time>.
    pre_condition: start_time > end_time
    """
    delta = end_time - start_time
    delta = int(delta.total_seconds() // 60)
    return delta


if __name__ == '__main__':
    import python_ta
    python_ta.check_all(config={
        'allowed-import-modules': [
            'doctest', 'python_ta', 'typing',
            'datetime'
        ],
        'max-attributes': 15
    })
