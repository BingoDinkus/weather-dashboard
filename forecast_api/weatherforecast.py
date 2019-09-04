'''
    Abstract base class
    Each Weather API service should inherit from this class
    and flesh out it's methods.

    Uses the National Weather Service API for alerts,
    for when a service doesn't include this information.
'''

__author__ = 'Eric J. Harlan'
__license__ = "GPLv3"

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
import logging
import requests

from forecast_api.weatheralert import WeatherAlert, WeatherAlertsCollection
from forecast_api.forecastdata import ForecastDataCollection

log = logging.getLogger(__name__)

class WeatherServices(Enum):
    ACCUWEATHER = 1
    DARKSKY = 2

WeatherServices_Display_Names = {
    1: 'AccuWeather'
    , 2: 'DarkSky'
}

class UnitType(Enum):
    METRIC = 1
    IMPERIAL = 2

class WeatherForecast(ABC):
    '''
        Base class that for weather forecasting.
        Each service inherits from this class.
    '''
    def __init__(self, weather_service, unit_type, lat_long, api_key=None, nws_user_agent=None):
        # Parameter assignment
        self.weather_service = weather_service
        self.weather_service_display_name = WeatherServices_Display_Names[weather_service.value]
        self.has_nighttime_forecasts = None
        self.api_key = api_key
        self.unit_type = unit_type
        self.lat_long = lat_long
        self.nws_user_agent = nws_user_agent

        self._base_url = None

        # Attributes
        self.city = None
        self.state = None
        self.state_abbrev = None
        self.country = None
        self.country_abbrev = None
        self.forecast_updated = False # Used to determine if screen needs refresh

        # Utility
        # Used to translate API response to weather font character
        self._weather_icon_map = {}
        self._precip_icon_map = {
            'rain': '\uf084' # umbrella
            , 'snow': '\uf076' # snowflake
        }

        # ForecastData objects
        self.current_conditions = ForecastDataCollection()
        self.hourly_forecasts = ForecastDataCollection()
        self.daily_forecasts = ForecastDataCollection()
        self.alerts = WeatherAlertsCollection()

    def __repr__(self):
        return (f'Weather Service: {self.weather_service}\n'
            f'Unit Type: {self.unit_type}\n'
            'Current Conditions:\n'
            f'\tForecast Date: {self.current_conditions.forecasts[0].forecast_datetime}\n'
            f'\tCurrent Temp: {self.current_conditions.forecasts[0].current_temperature.temperature}\n'
            f'\tFeels Like: {self.current_conditions.forecasts[0].feels_like_temperature.temperature}\n'
            # Terminal can't display fonts, use raw response
            f'\tCurrent Icon: {self.current_conditions.forecasts[0].weather_icon_raw}\n'
            f'\tWeather Text: {self.current_conditions.forecasts[0].weather_text}\n'
            f'\tRelative Humidity: {self.current_conditions.forecasts[0].relative_humidity}\n'
            f'\tHigh/Low: {self.current_conditions.forecasts[0].high_temperature.temperature} '
            f'/ {self.current_conditions.forecasts[0].low_temperature.temperature}\n'
            f'\tPrecip. Probab: {self.current_conditions.forecasts[0].precipitation_probability}%'
        )

    def __str__(self):
        return (f'In {self.city}, it is currently '
            f'{self.current_conditions.forecasts[0].current_temperature.temperature} '
            f'(feels like {self.current_conditions.forecasts[0].feels_like_temperature.temperature}) '
            f'and {str(self.current_conditions.forecasts[0].weather_text).lower()}.'
        )

    @abstractmethod
    def refresh(self):
        ''' To be implemented by derived class '''
        pass

    def _get_alerts(self):
        # Make request to NWS Alerts endpoint
        url = 'https://api.weather.gov/alerts/active'

        headers = {
            'Accept': 'application/geo+json'
            , 'User-Agent': self.nws_user_agent
        }

        params = {
            'point': self.lat_long
            , 'status': 'actual'
        }

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        j = response.json()

        # DEBUG - read json from file instead of api request
        # with open('Sample Responses/NWS/alerts.json') as json_file:
        #     j = json.load(json_file)

        # Parse response, creating WeatherAlertsCollection object
        alerts = []
        for item in j.get('features', []):
            prop = item['properties']
            effective_start_raw = prop['effective']
            effective_start = datetime.strptime(effective_start_raw, '%Y-%m-%dT%H:%M:%S%z')

            effective_end_raw = prop['ends']
            effective_end = datetime.strptime(effective_end_raw, '%Y-%m-%dT%H:%M:%S%z')

            new_alert = WeatherAlert(
                prop['event']                   # title
                , prop['areaDesc'].split(';')   # regions
                , prop['severity']              # severity
                , prop['description']           # description
                , effective_start               # effective_start
                , effective_end                 # effective_end
            )

            alerts.append(new_alert)

        alerts_collection = WeatherAlertsCollection(
            alerts= alerts
            , next_refresh= datetime.now() + timedelta(minutes=30)
        )

        # If response matches existing data, indicate that the alerts weren't updated
        # Always update the object so next_refresh is accurate
        if self.alerts == alerts_collection:
            alerts_updated = False
        else:
            alerts_updated = True

        self.alerts = alerts_collection
        return alerts_updated

    def get_next_refresh(self):
        '''
            Returns the nearest refresh time from all members of object
        '''

        log.debug(f'Current Conditions next refresh: {self.current_conditions.next_refresh}')
        log.debug(f'Hourly Forecast next refresh: {self.hourly_forecasts.next_refresh}')
        log.debug(f'Daily Forecast next refresh: {self.daily_forecasts.next_refresh}')
        log.debug(f'Alerts next refresh: {self.alerts.next_refresh}')

        return min(self.current_conditions.next_refresh
                    , self.hourly_forecasts.next_refresh
                    , self.daily_forecasts.next_refresh
                    , self.alerts.next_refresh
                )

    def get_daytime_forecasts(self):
        forecasts = self.daily_forecasts.forecasts
        return [f for f in forecasts if f.is_nighttime_forecast == False]

    def get_nighttime_forecasts(self):
        forecasts = self.daily_forecasts.forecasts
        return [f for f in forecasts if f.is_nighttime_forecast == True]
