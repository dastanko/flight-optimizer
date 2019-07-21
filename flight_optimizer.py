import argparse as arg
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pprint import pprint
from typing import Iterable

import requests as rq
from haversine import haversine as calc_distance

DATE_FORMAT = "%d/%m/%Y"

AGGREGATION_FLIGHTS_URL = "https://api.skypicker.com/aggregation_flights"
LOCATIONS_URL = "https://api.skypicker.com/locations"


@dataclass
class Airport:
    city: str
    name: str
    code: str
    rank: int
    loc: tuple


@dataclass
class Flight:
    departure: Airport
    destination: Airport
    distance: float
    price: float


class NoSuchCity(Exception):
    def __init__(self, city: str) -> None:
        super().__init__(f'{city} city not found')


class NoDestinationCitiesProvided(Exception):
    pass


class FlightCalculator:

    def __init__(self, departure: str, destinations: Iterable[str]) -> None:
        self.departure = departure
        self.destinations = destinations

    def process(self) -> Iterable[Flight]:
        dep_airport = self.get_city_airport(self.departure)
        dest_airports = self.get_destination_airports(self.destinations)

        for dest_airport in dest_airports:
            distance = calc_distance(dep_airport.loc, dest_airport.loc)
            price = self.get_best_price(dep_airport, dest_airport)
            yield Flight(dep_airport, dest_airport, distance, price)

    def get_destination_airports(self, cities: Iterable[str]) -> Iterable[Airport]:
        if len(cities) == 0:
            raise NoDestinationCitiesProvided
        return [self.get_city_airport(city) for city in cities]

    def get_city_airport(self, city: str) -> Airport:
        query = {
            'term': city,
            'location_types': 'airport',
            'active_only': 'true',
            'limit': 1,  # get most popular airport in the city
            'sort': 'rank'
        }

        data = rq.get(LOCATIONS_URL, params=query).json()

        if 'locations' not in data or len(data['locations']) == 0:
            raise NoSuchCity(city=city)

        airport = data['locations'][0]

        return Airport(city,
                       airport["name"],
                       airport["code"],
                       airport["rank"], (
                           airport["location"]["lat"],
                           airport["location"]["lon"])
                       )

    def get_best_price(self, dep_airport: Airport, dest_airport: Airport) -> float:
        query = {
            'fly_from': f'airport:{dep_airport.code}',
            'fly_to': f'airport:{dest_airport.code}',
            'date_from': date.today().strftime(DATE_FORMAT),
            'date_to': (date.today() + timedelta(days=1)).strftime(DATE_FORMAT),
            'flight_type': "round",
            'curr': 'USD'
        }
        response = rq.get(AGGREGATION_FLIGHTS_URL, params=query, headers={'X-API-Version': '1'})
        data: dict = response.json()

        if 'best_results' not in data and len(data['best_results']) == 0:
            return None

        return data["best_results"][0]['price']


if __name__ == '__main__':
    parser = arg.ArgumentParser()
    parser.add_argument("--from", dest='departure', metavar='<city>', type=str, required=True,
                        help="specifies departure city.")
    parser.add_argument("--to", dest='destinations', metavar='<city>', nargs='+', required=True, type=str,
                        help="specifies list of destination cities.")

    args = parser.parse_args()
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    calculator = FlightCalculator(args.departure, args.destinations)

    for flight in calculator.process():
        pprint(flight)
