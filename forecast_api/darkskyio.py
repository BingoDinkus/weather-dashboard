'''
    Derived from WeatherForecast
    Responsible for handling all DarkSky API calls
    and update WeatherForecast object
'''

__author__ = 'Eric J. Harlan'
__license__ = "GPLv3"

from forecast_api.forecastdata import *
from forecast_api.weatherforecast import *

from datetime import datetime, timedelta
import json
import logging
import requests

log = logging.getLogger(__name__)

class DarkSkyIO(WeatherForecast):
    def __init__(self, api_key, unit_type, lat_long):
        self._MAX_API_CALLS = 1000 # Service offers 1,000 per day for free

        WeatherForecast.__init__(self
                                , weather_service= WeatherServices.DARKSKY
                                , unit_type= unit_type
                                , lat_long= lat_long
                                , api_key= api_key)
        self.has_nighttime_forecasts = False
        self._base_url = 'https://api.darksky.net'
        self.api_calls_remaining = self._MAX_API_CALLS

        self._weather_icon_map = {
            'clear-day': '\uf00d'
            , 'clear-night': '\uf02e'
            , 'rain': '\uf019'
            , 'snow': '\uf01b'
            , 'sleet': '\uf0b5'
            , 'wind': '\uf011'
            , 'fog': '\uf014'
            , 'cloudy': '\uf013'
            , 'partly-cloudy-day': '\uf002'
            , 'partly-cloudy-night': '\uf086'
            , 'hail': '\uf015'
            , 'thunderstorm': '\uf01e'
            , 'tornado': '\uf056'
        }

        self._headers = {
            'Accept-Encoding': 'gzip'
            , 'Accept-Language': 'en-US'
        }

    def _make_request(self):
        '''
            Makes a Forecast Request API call to the DarkSky IO service
            Since all info is returned with one API call,
                all functions will simply call this function

            https://darksky.net/dev/docs#forecast-request
        '''
        log.debug('Entering _make_request()')

        url = f'{self._base_url}/forecast/{self.api_key}/{self.lat_long}'

        if self.unit_type == UnitType.IMPERIAL:
            units = 'us'
        else:
            units = 'si'

        params = {
            'lang': 'en'
            , 'units': units
            , 'exclude': 'minutely, flags'
        }

        response = requests.get(url, headers=self._headers, params=params)
        response.raise_for_status()

        # log.debug('Response Headers:')
        # for header, val in response.headers.items():
        #     log.debug(f'{header:35s}{val}')

        # log.debug(f'Response: {response.json()}')

        # Parse calls used from header, use to set calls remaining
        api_calls_used = int(response.headers['X-Forecast-API-Calls'])
        self.api_calls_remaining = self._MAX_API_CALLS - api_calls_used
        log.info(f'{self.api_calls_remaining} DarkSky API calls remaining')

        j = response.json()
        current_refresh = self._parse_current_conditions(j['currently'])
        hourly_refresh = self._parse_hourly_conditions(j['hourly']['data'])
        daily_refresh = self._parse_daily_conditions(j['daily']['data'])
        alerts_refresh = self._parse_alerts(j.get('alerts', None))

        log.debug('Exiting _make_request()')
        return current_refresh or hourly_refresh or daily_refresh or alerts_refresh

    def _parse_forecast(self, forecast_json):
        '''
            The DarkSky responses are consistent across current/hourly/daily
            forecasts.

            This function handles them to repeat duplicate code
        '''

        sunrise = None
        sunset = None
        precipitation_probability = None
        if 'sunriseTime' in forecast_json:
            sunrise = datetime.fromtimestamp(forecast_json['sunriseTime'])
        if 'sunsetTime' in forecast_json:
            sunset = datetime.fromtimestamp(forecast_json['sunsetTime'])
        if 'precipProbability' in forecast_json:
            precipitation_probability = forecast_json['precipProbability'] * 100

        precipitation_type = forecast_json.get('precipType', None)
        precipitation_icon = self._precip_icon_map.get(str(precipitation_type).lower(), '\uf084')

        forecast = ForecastData(
            forecast_datetime= datetime.fromtimestamp(forecast_json['time'])
            , is_nighttime_forecast= False
            , current_temperature= forecast_json.get('temperature', None)
            , feels_like_temperature= forecast_json.get('apparentTemperature', None)
            , relative_humidity= forecast_json['humidity'] * 100

            , high_temperature= forecast_json.get('temperatureMax', None)
            , low_temperature= forecast_json.get('temperatureMin', None)
            , feels_like_high= forecast_json.get('apparentTemperatureHigh', None)
            , feels_like_low= forecast_json.get('apparentTemperatureLow', None)

            , precipitation_type= precipitation_type
            , precipitation_icon= precipitation_icon
            , precipitation_probability= precipitation_probability
            , precipitation_amount= forecast_json.get('precipAccumulation', None)

            , weather_icon_raw= forecast_json['icon']
            , weather_icon= self._weather_icon_map[forecast_json['icon']]
            , weather_text= forecast_json['summary']

            , sunrise_time= sunrise
            , sunset_time= sunset
        )

        return forecast

    def _parse_current_conditions(self, forecast_json, refresh_interval_minutes=60):
        '''
            Handles parsing current condition data and updating object
        '''
        log.debug('Entering _parse_current_conditions()')

        forecast = self._parse_forecast(forecast_json)
        forecast_collection = ForecastDataCollection(
            forecasts= [forecast]
            # Set forecast expiration time to 1 hour from now
            , next_refresh= datetime.now()
                            + timedelta(minutes=refresh_interval_minutes)
        )

        # If response matches existing data, indicate that the forecast wasn't updated
        # Always update the object so next_refresh is accurate
        if self.current_conditions == forecast_collection:
            forecast_updated = False
        else:
            forecast_updated = True

        self.current_conditions = forecast_collection

        log.debug('Exiting _parse_current_conditions()')
        return forecast_updated

    def _parse_hourly_conditions(self, response, refresh_interval_minutes=60):
        '''
            Handles parsing current condition data and updating object
        '''
        log.debug('Entering _parse_current_conditions()')

        # Loop through all forecast items, adding them to a list
        forecasts = []

        log.debug(f'Parsing {len(response)} elements...')
        for item in response:
            forecasts.append(self._parse_forecast(item))

        forecast_collection = ForecastDataCollection(
            forecasts= forecasts
            # Set forecast expiration time to 1 hour from now
            , next_refresh= datetime.now()
                            + timedelta(minutes=refresh_interval_minutes)
        )

        # If response matches existing data, indicate that the forecast wasn't updated
        # Always update the object so next_refresh is accurate
        if self.hourly_forecasts == forecast_collection:
            forecast_updated = False
        else:
            forecast_updated = True

        self.hourly_forecasts = forecast_collection

        log.debug('Exiting _parse_current_conditions()')
        return forecast_updated

    def _parse_daily_conditions(self, response, refresh_interval_minutes=60):
        '''
            Handles parsing current condition data and updating object
        '''
        log.debug('Entering _parse_daily_conditions()')

        forecasts = []

        log.debug(f'Parsing {len(response)} elements...')
        for item in response:
            forecasts.append(self._parse_forecast(item))

        forecast_collection = ForecastDataCollection(
            forecasts= forecasts
            # Set forecast expiration time to 1 hour from now
            , next_refresh= datetime.now()
                            + timedelta(minutes=refresh_interval_minutes)
        )

        # If response matches existing data, indicate that the forecast wasn't updated
        # Always update the object so next_refresh is accurate
        if self.daily_forecasts == forecast_collection:
            forecast_updated = False
        else:
            forecast_updated = True

        self.daily_forecasts = forecast_collection

        log.debug('Exiting _parse_daily_conditions()')
        return forecast_updated

    def _parse_alerts(self, response, refresh_interval_minutes=30):
        log.debug('Entering _parse_alerts()')

        # If there's no alerts data, create empty collection and update next_refresh
        if response is None:
            alerts_collection = WeatherAlertsCollection(
                alerts= []
                # Set forecast expiration time to 30 minutes from now
                , next_refresh= datetime.now()
                                + timedelta(minutes=refresh_interval_minutes)
            )

        # Alert response exists, parse it
        else:
            alerts = []
            for item in response:
                effective_start= datetime.fromtimestamp(item['time'])
                effective_end= datetime.fromtimestamp(item['expires'])

                new_alert = WeatherAlert(
                    title= item['title']
                    , regions= item['regions']
                    , severity= item['severity']
                    , description= item['description']
                    , effective_start= effective_start
                    , effective_end= effective_end
                )

                alerts_collection = WeatherAlertsCollection(
                    alerts= alerts
                    # Set forecast expiration time to 30 minutes from now
                    , next_refresh= datetime.now()
                                    + timedelta(minutes=refresh_interval_minutes)
                )

        # If response matches existing data, indicate that the alerts weren't updated
        # Always update the object so next_refresh is accurate
        if self.alerts == alerts_collection:
            alerts_updated = False
        else:
            alerts_updated = True

        self.alerts = alerts_collection

        log.debug('Exiting _parse_alerts()')
        return alerts_updated

    def _get_alerts(self):
        logging.critical('This method should not be called directly for this service. '
                         'Alerts are included in standard data payload.'
        )
        raise NotImplementedError

    def refresh(self):
        '''
            Handles logic for determining if forecast needs to be refreshed
            and updating as needed

            Returns whether or not any forecast object has changed
        '''
        log.debug('Entering refresh()')

        if datetime.now() >= self.get_next_refresh():
            return_value = self._make_request()
        else:
            return_value = False

        log.debug(f'Exiting refresh() with status: {return_value}')
        return return_value
