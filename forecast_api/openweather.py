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
    def __init__(self, api_key, unit_type, lat_long, time_zone, lang):
        self._MAX_API_CALLS = 1000 # Service offers 1,000 per day for free

        super().__init__(
                weather_service= 'OpenWeather'
                , unit_type= unit_type
                , lat_long= lat_long
                , time_zone= time_zone

                , api_key= api_key
                , lang= lang
        )
        self.has_nighttime_forecasts = False
        self.api_calls_remaining = self._MAX_API_CALLS

        self._base_url = 'https://api.openweathermap.org/data/3.0/'
        self._timezone_offset = 0

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
            icon_dict = self._weather_icon_map.get(icon_name)

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
                weather_icon = self._weather_icon_map['unknown']

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

        params = {
            'lat': {self.lat},
            'lon': {self.long},
            'appid': {self.api_key},
            'units': {self.unit_type},
            'lang': {self.lang},
            'exclude': 'minutely,alerts'
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
        except Exception as err: #requests.exceptions.HTTPError as err:
            log.exception('Request failed.')

            self._log_response_details(response)

            new_refresh = datetime.now() + timedelta(hours=1)
            log.error(f'OpenWeather request failed. Setting next refresh for {new_refresh}.')
            self.current_conditions.next_refresh = new_refresh
            self.hourly_forecasts.next_refresh = new_refresh
            self.daily_forecasts.next_refresh = new_refresh
            self.alerts.next_refresh = new_refresh

            # Return False indicating nothing was updated
            return False

        try:
            j = response.json()
            self._timezone_offset = j.get('timezone_offset', 0)

            current_refresh = self._parse_current_conditions(j['current'])
            hourly_refresh = self._parse_hourly_conditions(j['hourly'])
            daily_refresh = self._parse_daily_conditions(j['daily'])
            alerts_refresh = self._get_alerts()
        except Exception:
            # Log exception and dump json to file for debugging
            log.exception('Failed to parse forecast')

            with open(f'openweather response {datetime.now().strftime("%Y-%m-%d %H%M%S")}.json', 'w') as f:
                f.write(response.text)

            # Rethrow exception
            raise

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
        if 'pop' in forecast_json:
            precipitation_probability = forecast_json['pop'] * 100

        # OpenWeather doesn't provide the overall precipitation type
        # Use the Rain and Snow pop to determine which icon to display
        # The object for rain/snow varies depending on the section
        # Parse the value from the 1h element as needed
        rain_mm = forecast_json.get('rain', 0)
        if isinstance(rain_mm, dict):
            rain_mm = rain_mm['1h']

        snow_mm = forecast_json.get('snow', 0)
        if isinstance(snow_mm, dict):
            snow_mm = snow_mm['1h']

        precipitation_accumulation = rain_mm + snow_mm

        if rain_mm >= snow_mm:
            precipitation_type = 'rain'
        else:
            precipitation_type = 'snow'

        precipitation_icon = self._precip_icon_map.get(precipitation_type, '\uf084')

        # For current and hourly, the API provides a single temp for "temp" and "feels_like"
        # For daily, the API provides an object with temp and feels_like temps throughout the day
        # If temp or feels_like is a json/dict, grab the "day" element as the value

        # temp
        temp_min = None
        temp_max = None
        temp = forecast_json['temp']
        if isinstance(temp, dict):
            temp_min = temp['min']
            temp_max = temp['max']
            temp = temp['day']

        # feels_like
        feels_like_min = None
        feels_like_max = None
        feels_like = forecast_json['feels_like']
        if isinstance(feels_like, dict):
            feels_like_list = [
                                feels_like['day'],
                                feels_like['night'],
                                feels_like['eve'],
                                feels_like['morn']
                            ]
            feels_like_min = min(feels_like_list)
            feels_like_max = max(feels_like_list)
            feels_like = feels_like['day']

        # Current and Hourly do not have a summary
        # Use the weather.description element instead, convert to title case
        if 'summary' in forecast_json:
            weather_text = forecast_json['summary']
        else:
            weather_text = str(forecast_json['weather'][0]['description']).title()

        # Derive the icon from the icon + decription info
        weather_icon = self._get_weather_icon(forecast_json['weather'][0]['icon'], forecast_json['weather'][0]['description'])

        forecast = ForecastData(
            forecast_datetime= datetime.fromtimestamp(forecast_json['dt'])
            , is_nighttime_forecast= False
            , current_temperature= temp
            , feels_like_temperature= feels_like
            , relative_humidity= forecast_json['humidity']

            , low_temperature= temp_min
            , high_temperature= temp_max
            , feels_like_low= feels_like_min
            , feels_like_high= feels_like_max

            , precipitation_type= precipitation_type
            , precipitation_icon= precipitation_icon
            , precipitation_probability= precipitation_probability
            , precipitation_amount= precipitation_accumulation

            , weather_text= weather_text
            , weather_icon_raw= forecast_json['weather'][0]['icon']
            , weather_icon= weather_icon

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
        log.debug('Entering _parse_hourly_conditions()')

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

        log.debug('Exiting _parse_hourly_conditions()')
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