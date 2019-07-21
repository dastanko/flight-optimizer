import json
import subprocess as sb
import unittest
from unittest import mock

from flight_optimizer import FlightCalculator, NoSuchCity, Flight, Airport, NoDestinationCitiesProvided, LOCATIONS_URL


class FakeResponse(object):
    def __init__(self, data: dict) -> None:
        self.data = data

    def json(self):
        return self.data


def get_location_fixture(params):
    with open('locations.json', 'r') as file:
        cities = json.loads(file.read())
    return FakeResponse(cities[params['term']])


def get_best_price_fixture(params):
    with open('best_prices.json', 'r') as file:
        best_prices = json.loads(file.read())
    return FakeResponse(best_prices[f'{params["fly_from"]}-{params["fly_to"]}'])


def mocked_request(url, params=None, **kwargs):
    if url == LOCATIONS_URL:
        return get_location_fixture(params)
    else:
        return get_best_price_fixture(params)


class FlightCalculatorTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.london = Airport(city='london', name='Gatwick', code='LGW', rank=2, loc=(51.148056, -0.190278))
        self.paris = Airport(city='paris', name='Charles de Gaulle Airport', code='CDG', rank=1,
                             loc=(49.009722, 2.547778))
        self.berlin = Airport(city='berlin', name='Berlin Tegel', code='TXL', rank=5, loc=(52.559722, 13.287778))
        self.flight1 = Flight(departure=self.london,
                              destination=self.paris,
                              distance=307.7037132860935,
                              price=134)
        self.flight2 = Flight(departure=self.london,
                              destination=self.berlin,
                              distance=937.4718926444107,
                              price=230)

    @mock.patch('requests.get', side_effect=mocked_request)
    def test_empty_dest_and_dep(self, mockk):
        with self.assertRaises(NoSuchCity) as ex_context:
            list(FlightCalculator('', []).process())

        self.assertEqual(ex_context.exception.args[0], ' city not found')

    @mock.patch('requests.get', side_effect=mocked_request)
    def test_empty_departure(self, mockk):
        with self.assertRaises(NoSuchCity) as ex_context:
            list(FlightCalculator('', ['paris']).process())

        self.assertEqual(ex_context.exception.args[0], ' city not found')

    @mock.patch('requests.get', side_effect=mocked_request)
    def test_empty_destination(self, mockk):
        with self.assertRaises(NoDestinationCitiesProvided):
            list(FlightCalculator('london', []).process())

    @mock.patch('requests.get', side_effect=mocked_request)
    def test_nonexistent_departure_city(self, mockk):
        with self.assertRaises(NoSuchCity) as ex_context:
            list(FlightCalculator('abra_cadabra', []).process())

        self.assertEqual(ex_context.exception.args[0], 'abra_cadabra city not found')

    @mock.patch('requests.get', side_effect=mocked_request)
    def test_nonexistent_destination_city(self, mockk):
        with self.assertRaises(NoSuchCity) as ex_context:
            list(FlightCalculator('london', ['abra_cadabra']).process())

        self.assertEqual(ex_context.exception.args[0], 'abra_cadabra city not found')

    @mock.patch('requests.get', side_effect=mocked_request)
    def test_from_london_to_paris(self, mockk):
        calculator = FlightCalculator('london', ['paris'])

        flights = list(calculator.process())
        self.assertEqual(1, len(flights))
        self.assertEqual([self.flight1], flights)

    @mock.patch('requests.get', side_effect=mocked_request)
    def test_with_several_destination_cities(self, mockk):
        calculator = FlightCalculator('london', ['paris', 'berlin'])

        flights = list(calculator.process())
        self.assertEqual(2, len(flights))
        self.assertEqual([self.flight1, self.flight2], flights)


help_output = """usage: flight_optimizer.py [-h] --from <city> --to <city> [<city> ...]

optional arguments:
  -h, --help            show this help message and exit
  --from <city>         specifies departure city.
  --to <city> [<city> ...]
                        specifies list of destination cities.
"""


class SmokeTestCase(unittest.TestCase):
    def test_show_help(self):
        result = self._run('python flight_optimizer.py -h')
        self.assertEqual(help_output, result.stdout)

    def test_sample_run(self):
        result = self._run('python flight_optimizer.py --from London --to Paris')
        self.assertRegex(result.stdout, r'London, Gatwick --> Paris, Charles de Gaulle Airport ::: \d+\.\d+km / \d+\$ = \d+\.\d+\$ per km')

    def _run(self, command):
        return sb.run(command, shell=True, text=True, stdout=sb.PIPE, stderr=sb.PIPE)
