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
import logging
import requests

from forecast_api.weatheralert import WeatherAlert, WeatherAlertsCollection
from forecast_api.forecastdata import ForecastDataCollection

log = logging.getLogger(__name__)

class WeatherForecast(ABC):
    '''
        Base class that for weather forecasting.
        Each service inherits from this class.
    '''
    def __init__(self, weather_service, unit_type, lat_long, time_zone, api_key=None, lang=None, nws_user_agent=None):
        # Parameter assignment
        self.weather_service = weather_service
        self.has_nighttime_forecasts = None
        self.api_key = api_key
        self.unit_type = unit_type
        self.lat_long = lat_long
        self.lat = lat_long.split(',')[0]
        self.long = lat_long.split(',')[1]
        self.time_zone= time_zone
        self.lang = lang
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

    def _log_response_details(self, response):
        log.debug('Response Headers:')
        for header, val in response.headers.items():
            log.debug(f'\t{header:35s}{val}')

        json_response = None
        try:
            json_response = response.json()
        except:
            log.exception('Failed to get response JSON')

        if json_response:
            log.debug(f'Response JSON:')
            log.debug(f'\t{json_response}')

    def _get_alerts(self):
        log.debug('Entering _get_alerts()')

        alerts_updated = False

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

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
        except Exception as err: #requests.exceptions.HTTPError as err:
            log.exception(f'Alerts request failed.')

            self._log_response_details(response)

            new_refresh = datetime.now() + timedelta(minutes=30)
            log.error(f'Weather.gov Alert request failed. Setting next refresh for {new_refresh}.')
            self.alerts.next_refresh = new_refresh

            return alerts_updated

        j = response.json()

        # Parse response, creating WeatherAlertsCollection object
        alerts = []
        try:
            for item in j.get('features', []):
                prop = item['properties']
                effective_start_raw = prop['effective']
                effective_start = datetime.strptime(effective_start_raw, '%Y-%m-%dT%H:%M:%S%z')
                # NWS returns a timezone aware datetime, already in local time
                # Strip out the time zone so that comparisons don't break
                effective_start = effective_start.replace(tzinfo=None)

                effective_end_raw = prop['ends']
                effective_end = datetime.strptime(effective_end_raw, '%Y-%m-%dT%H:%M:%S%z')
                effective_end = effective_end.replace(tzinfo=None)

                new_alert = WeatherAlert(
                    prop['event']                   # title
                    , prop['areaDesc'].split(';')   # regions
                    , prop['severity']              # severity
                    , prop['description']           # description
                    , effective_start               # effective_start
                    , effective_end                 # effective_end
                )

                alerts.append(new_alert)
        except Exception as err:
            log.exception('Malformed alerts response.')

            self._log_response_details(response)

            new_refresh = datetime.now() + timedelta(minutes=30)
            log.error(f'Failed to parse Weather.gov alerts. Setting next refresh for {new_refresh}.')
            self.alerts.next_refresh = new_refresh

            return alerts_updated

        alerts_collection = WeatherAlertsCollection(
            alerts= alerts
            , next_refresh= datetime.now() + timedelta(minutes=30)
        )

        # If response does not match existing data, indicate that the alerts were updated
        # Always update the object so next_refresh is accurate
        if self.alerts != alerts_collection:
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
