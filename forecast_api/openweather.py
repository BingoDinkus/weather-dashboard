'''
    Derived from WeatherForecast
    Responsible for handling all OpenWeather API calls
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

class OpenWeather(WeatherForecast):
    def __init__(self, api_key, unit_type, lat_long, lang):
        self._MAX_API_CALLS = 1000 # Service offers 1,000 per day for free

        WeatherForecast.__init__(self
                                , weather_service= WeatherServices.DARKSKY
                                , unit_type= unit_type
                                , lat_long= lat_long

                                , api_key= api_key
                                , lang= lang
                        )
        self.has_nighttime_forecasts = False
        self._base_url = 'https://api.openweathermap.org/data/3.0/'
        self.api_calls_remaining = self._MAX_API_CALLS

        self._weather_icon_map = {
            # https://openweathermap.org/weather-conditions#Weather-Condition-Codes-2

            # Clear - Day
            '01d': {'default': '\uf00d'},   # wi-day-sunny
            # Clear - Night
            '01n': {'default': '\uf02e'},   # wi-night-clear

            # Few Clouds (11-25%) - Day
            '02d': {'default': '\uf002'},   # wi-day-cloudy
            # Few Clouds (11-25%) - Night
            '02n': {'default': '\uf086'},   # wi-night-alt-cloudy

            # Scattered Clouds (25-50%) - Day
            '03d': {'default': '\uf041'},   # wi-cloud
            # Scattered Clouds (25-50%) - Night
            '03n': {'default': '\uf041'},   # wi-cloud

            # Broken Clouds (51%+) - Day
            '04d': {'default': '\uf013'},   # wi-cloudy
            # Broken Clouds (51%+) - Night
            '04n': {'default': '\uf013'},   # wi-cloudy

            # Drizzle - Day
            '09d': {'default': '\uf009'},   # wi-day-showers
            # Drizzle - Night
            '09n': {'default': '\uf029'},   # wi-night-alt-showers

            # Rain - Day
            '10d': {
                'default': '\uf008',        # wi-day-rain
                # light rain
                500: '\uf009',              # wi-day-showers
                # freezing rain
                511: '\uf006',              # wi-day-rain-mix

                # light intensity shower rain
                520: '\uf019',              # wi-rain
                # shower rain
                521: '\uf019',              # wi-rain
                # heavy intensity shower rain
                522: '\uf019',              # wi-rain
                # ragged shower rain
                531: '\uf019'               # wi-rain

            },
            # Rain - Night
            '10n': {
                'default': '\uf028',        # wi-night-alt-rain
                # light rain
                500: '\uf029',            # wi-night-alt-showers
                # freezing rain
                511: '\uf026',            # wi-night-alt-rain-mix

                # light intensity shower rain
                520: '\uf019',              # wi-rain
                # shower rain
                521: '\uf019',              # wi-rain
                # heavy intensity shower rain
                522: '\uf019',              # wi-rain
                # ragged shower rain
                531: '\uf019'               # wi-rain
            },

            # Thunderstorm - Day
            '11d': {'default': '\uf01e'},   # wi-thunderstorm
            # Thunderstorm - Night
            '11n': {'default': '\uf01e'},   # wi-thunderstorm

            # Snow - Day
            '13d': {
                'default': '\uf00a',                # wi-day-snow
                'heavy snow': '\uf01b',             # wi-snow
                'sleet': '\uf0b2',                  # wi-day-sleet
                'light rain and snow': '\uf0b2',    # wi-day-sleet
                'rain and snow': '\uf0b2',          # wi-day-sleet
                'light shower snow': '\uf0b2',      # wi-day-sleet
                'shower snow': '\uf0b2',            # wi-day-sleet
                'heavy shower snow': '\uf0b5'       # wi-sleet
            },
            # Snow - Night
            '13n': {
                'default': '\uf02a',                # wi-night-alt-snow
                'heavy snow': '\uf01b',             # wi-snow
                'sleet': '\uf0b4',                  # wi-night-alt-sleet
                'light rain and snow': '\uf0b4',    # wi-night-alt-sleet
                'rain and snow': '\uf0b4',          # wi-night-alt-sleet
                'light shower snow': '\uf0b4',      # wi-night-alt-sleet
                'shower snow': '\uf0b4',            # wi-night-alt-sleet
                'heavy shower snow': '\uf0b5'       # wi-sleet
            },

            # Mist, etc - Day
            '50d': {
                'default': '\uf0b6',        # wi-day-haze
                'fog': '\uf003',            # wi-day-fog
                'squalls': '\uf085',        # wi-day-windy
                'tornado': '\uf056'         # wi-tornado


            },
            # Mist, etc - Night
            '50n': {
                'default': '\uf063',        # wi-dust
                'fog': '\uf04a',            # wi-night-fog
                'squalls': '\uf02f',        # wi-night-cloudy-gusts
                'tornado': '\uf056'         # wi-tornado
            },

            # For anything unmapped, use the Alien icon
            'unknown': '\uf075'             # wi-alien
        }

    def _get_weather_icon(self, icon_name, description='default'):
        '''
            A helper function to handle returning the specified icon
            Falls back on the default if the specific condition does not have an icon
            If the icon is not found, the icon for "unknown" will be returned
        '''
        log.debug('Entering _get_weather_icon()')

        # Initialize icon to None
        weather_icon = None

        try:
            # Attempt to get the dictonary for the specified icon (e.g. "10d")
            icon_dict = weather_icon_map.get(icon_name)

            # If the icon is valid, a dictionary will be returned
            if isinstance(icon_dict, dict):
                # Attempt to get the glyph for the icon and description
                # If one isn't found, use the icon's default instead
                log.debug(f'Match found for {icon_name} : {description}')
                weather_icon = icon_dict.get(description, icon_dict.get('default'))
            else:
                log.debug(f'No dictionary found for icon {icon_name}')
        finally:
            # If we didn't manage to find a glyph, use the unknown glyph instead
            if not weather_icon:
                weather_icon = weather_icon_map['unknown']

        return weather_icon

        log.debug('Exiting _get_weather_icon()')

    def _make_request(self):
        '''
            Makes a Forecast Request API call to the OpenWeather service
            Since all info is returned with one API call,
                all functions will simply call this function

            https://openweathermap.org/api/one-call-3
        '''
        log.debug('Entering _make_request()')

        url = f'{self._base_url}/onecall'

        if self.unit_type == UnitType.IMPERIAL:
            units = 'imperial'
        else:
            units = 'metric'

        params = {
            'lat': {lat},
            'lon': {long},
            'appid': {api_key},
            'units': {units},
            'lang': {lang}
        }

        try:
            response = requests.get(url, headers=self._headers, params=params)
            response.raise_for_status()
        except Exception as err: #requests.exceptions.HTTPError as err:
            log.exception(f'Request failed.')

            self._log_response_details(response)

            new_refresh = datetime.now() + timedelta(hours=1)
            log.error(f'OpenWeather request failed. Setting next refresh for {new_refresh}.')
            self.current_conditions.next_refresh = new_refresh
            self.hourly_forecasts.next_refresh = new_refresh
            self.daily_forecasts.next_refresh = new_refresh
            self.alerts.next_refresh = new_refresh

            # Return False indicating nothing was updated
            return False

        # Parse calls used from header, use to set calls remaining
        api_calls_used = int(response.headers['X-Forecast-API-Calls'])
        self.api_calls_remaining = self._MAX_API_CALLS - api_calls_used
        log.info(f'{self.api_calls_remaining} OpenWeather API calls remaining')

        j = response.json()
        current_refresh = self._parse_current_conditions(j['currently'])
        hourly_refresh = self._parse_hourly_conditions(j['hourly']['data'])
        daily_refresh = self._parse_daily_conditions(j['daily']['data'])
        alerts_refresh = self._parse_alerts(j.get('alerts', None))

        log.debug('Exiting _make_request()')
        return current_refresh or hourly_refresh or daily_refresh or alerts_refresh

    def _parse_forecast(self, forecast_json):
        '''
            The OpenWeather responses are consistent across current/hourly/daily
            forecasts.

            This function handles them to repeat duplicate code
        '''

        sunrise = None
        sunset = None
        precipitation_probability = None
        if 'sunrise' in forecast_json:
            sunrise = datetime.fromtimestamp(forecast_json['sunrise'])
        if 'sunset' in forecast_json:
            sunset = datetime.fromtimestamp(forecast_json['sunset'])
        if 'daily.pop' in forecast_json:
            precipitation_probability = forecast_json['daily.pop'] * 100

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
            log.debug(f'Current conditions updated. Next refresh: {str(self.current_conditions.next_refresh)}')

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
            log.debug(f'Hourly forecast updated. Next refresh: {str(self.hourly_forecasts.next_refresh)}')

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
            log.debug(f'Daily forecast updated. Next refresh: {str(self.daily_forecasts.next_refresh)}')

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

                alerts.append(WeatherAlert(
                    title= item['title']
                    , regions= item['regions']
                    , severity= item['severity']
                    , description= item['description']
                    , effective_start= effective_start
                    , effective_end= effective_end
                ))

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
        log.debug(f'Alerts updated. Next refresh: {str(self.alerts.next_refresh)}')

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