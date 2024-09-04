'''
    Derived from WeatherForecast
    Responsible for handling all AccuWeather API calls
    and update WeatherForecast object
'''

__author__ = 'Eric J. Harlan'
__license__ = "GPLv3"

from forecast_api.forecastdata import *
from forecast_api.weatherforecast import *

from datetime import date, datetime, time, timedelta
import json
import logging
import requests

log = logging.getLogger(__name__)

class AccuWeather(WeatherForecast):
    def __init__(self, api_key, unit_type, lat_long, time_zone, nws_user_agent=None):
        self._MAX_API_CALLS = 50 # Free service offers 50 free api requests

        super().__init__(
            weather_service= 'AccuWeather'
            , unit_type= unit_type
            , lat_long= lat_long
            , time_zone= time_zone
            , api_key= api_key
            , nws_user_agent= nws_user_agent
        )
        self._location_key = None
        self._base_url = 'http://dataservice.accuweather.com'

        self.has_nighttime_forecasts = True
        self.api_calls_remaining = self._MAX_API_CALLS

        # refresh_tolerance_mins allows a refresh to occur if the
        # refresh is coming up in the near future
        self.refresh_tolerance_mins = 10

        self._weather_icon_map = {
            1: '\uf00d'     # Sunny
            , 2: '\uf00c'   # Mostly Sunny
            , 3: '\uf00c'   # Partly Sunny
            , 4: '\uf00c'   # Intermittent Clouds
            , 5: '\uf0b6'   # Hazy Sunshine
            , 6: '\uf002'   # Mostly Cloudy
            , 7: '\uf013'   # Cloudy
            , 8: '\uf013'   # Dreary (Overcast)
            , 11: '\uf014'  # Fog
            , 12: '\uf019'  # Showers
            , 13: '\uf002'  # Mostly Cloudy w/ Showers
            , 14: '\uf00c'  # Partly Sunny w/ Showers
            , 15: '\uf01e'  # T-Storms
            , 16: '\uf01d'  # Mostly Cloudy w/ T-Storms
            , 17: '\uf010'  # Partly Sunny w/ T-Storms
            , 18: '\uf019'  # Rain
            , 19: '\uf01b'  # Flurries
            , 20: '\uf00a'  # Mostly Cloudy w/ Flurries
            , 21: '\uf00a'  # Partly Sunny w/ Flurries
            , 22: '\uf01b'  # Snow
            , 23: '\uf00a'  # Mostly Cloudy w/ Snow
            , 24: '\uf0b5'  # Ice
            , 25: '\uf0b5'  # Sleet
            , 26: '\uf017'  # Freezing Rain
            , 29: '\uf017'  # Rain and Snow
            , 30: '\uf072'  # Hot
            , 31: '\uf076'  # Cold
            , 32: '\uf050'  # Windy
            , 33: '\uf02e'  # Clear
            , 34: '\uf081'  # Mostly Clear
            , 35: '\uf081'  # Partly Cloudy
            , 36: '\uf081'  # Intermittent Clouds
            , 37: '\uf04a'  # Hazy Moonlight
            , 38: '\uf086'  # Mostly Cloudy
            , 39: '\uf029'  # Partly Cloudy w/ Showers
            , 40: '\uf029'  # Mostly Cloudy w/ Showers
            , 41: '\uf02c'  # Partly Cloudy w/ T-Storms
            , 42: '\uf02c'  # Mostly Cloudy w/ T-Storms
            , 43: '\uf02a'  # Mostly Cloudy w/ Flurries
            , 44: '\uf02a'  # Mostly Cloudy w/ Snow
        }

        self._headers = {
            'Accept-Encoding': 'gzip'
            , 'Accept-Language': 'en-US'
        }

        self._get_location_key()

    def _make_request(self, end_point, headers, params={}):
        '''
            Makes an API call to the AccuWeather service
        '''
        log.debug(f'Entering _make_request() for endpoint {end_point}')

        url = f'{self._base_url}/{end_point}'

        # Add API Key to params
        params['apikey'] = self.api_key

        if self._location_key is None:
            lookup_success = self._get_location_key
        else:
            lookup_success = True

        if not lookup_success:
            log.error('Invalid location key. Request will not be made.')
        else:
            try:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
            except Exception as err: #requests.exceptions.HTTPError as err:
                log.exception(f'Request failed.')

                self._log_response_details(response)

            self.api_calls_remaining = int(response.headers.get('RateLimit-Remaining', -1))
            log.info(f'{self.api_calls_remaining} AccuWeather API calls remaining')

        log.debug('Exiting _make_request()')
        return response.json(), response.status_code

    def _get_location_key(self):
        '''
            https://www.developer.accuweather.com/accuweather-locations-api/apis/get/locations/v1/cities/geoposition/search

            Hits the GeoPosition Search end point
            If found, the Location Key of the top result is returned
            Otherwise, an error is thrown
        '''
        log.debug('Entering _get_location_key()')

        end_point = 'locations/v1/cities/geoposition/search'
        lookup_success = False

        if self._location_key is None:
            params = {'q': self.lat_long}
            response, response_status_code = self._make_request(end_point, self._headers, params)

            if response_status_code != requests.codes.ok: # pylint: disable=no-member
                new_refresh = datetime.now() + timedelta(hours=1)
                log.error(f'Location Key request failed. Setting next refresh for {new_refresh}.')

                self.current_conditions.next_refresh = new_refresh
                self.hourly_forecasts.next_refresh = new_refresh
                self.daily_forecasts.next_refresh = new_refresh
                self.alerts.next_refresh = new_refresh
            else:
                if 'Key' in response:
                    self._location_key = response.get('Key')
                    self.city = response.get('LocalizedName')
                    self.state = response.get('AdministrativeArea').get('LocalizedName')
                    self.state_abbrev = response.get('AdministrativeArea').get('ID')
                    self.country = response.get('Country').get('LocalizedName')
                    self.country_abbrev = response.get('Country').get('ID')

                    lookup_success = True
                else:
                    raise RuntimeError('Unable to find Location Key in response.')

        log.debug(f'Exiting _get_location_key() with status {lookup_success}')
        return lookup_success

    def _get_current_conditions(self):
        '''
            https://www.developer.accuweather.com/accuweather-current-conditions-api/apis/get/currentconditions/v1/%7BlocationKey%7D

            Hits the Current Conditions end point with the providied location_id
            and updates the current_conditions property

            Returns whether or not anything changed
        '''
        log.debug('Entering _get_current_conditions()')

        end_point = f'currentconditions/v1/{self._location_key}'
        forecast_updated = False

        # Get full details so that payload includes Real Feel
        params = {'details': 'true'}

        # Response is an list, grab the first (and only) item
        response, response_status_code = self._make_request(end_point, self._headers, params)

        if response_status_code != requests.codes.ok: # pylint: disable=no-member
            new_refresh = datetime.now() + timedelta(hours=1)
            log.error(f'Current Conditions request failed. Setting next refresh for {new_refresh}.')
            self.current_conditions.next_refresh = new_refresh
        else:
            response = response[0]

            # Create a new ForecastData object to store api response data
            forecast_date = response['LocalObservationDateTime']

            precipitation_type = response.get('PrecipitationType', None)
            precipitation_icon = self._precip_icon_map.get(str(precipitation_type).lower(), '\uf084')

            new_forecast = ForecastData(
                forecast_datetime= datetime.strptime(forecast_date, '%Y-%m-%dT%H:%M:%S%z')
                , current_temperature= response['Temperature'][str(self.unit_type.name).title()]['Value']
                , feels_like_temperature= response['RealFeelTemperature'][str(self.unit_type.name).title()]['Value']
                , weather_icon_raw= response['WeatherIcon']
                , weather_icon= self._weather_icon_map[response['WeatherIcon']]
                , weather_text= response['WeatherText']
                , relative_humidity= response['RelativeHumidity']

                , precipitation_type= precipitation_type
                , precipitation_icon= precipitation_icon
            )

            forecast_collection = ForecastDataCollection(
                forecasts=[new_forecast]
                # Set forecast refresh time to 1 hour from now
                , next_refresh= datetime.now() + timedelta(hours=1)
            )

            # If response doesn't match existing data, indicate that the forecast was updated
            # Always update the object so next_refresh is accurate
            if self.current_conditions != forecast_collection:
                forecast_updated = True

            self.current_conditions = forecast_collection

        log.debug('Exiting _get_current_conditions()')
        return forecast_updated

    def _get_hourly_forecast(self):
        '''
            https://www.developer.accuweather.com/accuweather-forecast-api/apis/get/forecasts/v1/hourly/12hour/%7BlocationKey%7D

            Hits the 12 hour forecast end point with the provided location_id
            and returns the response payload

            Returns whether or not anything changed
        '''
        log.debug('Entering _get_hourly_forecast()')

        end_point = f'forecasts/v1/hourly/12hour/{self._location_key}'
        forecast_updated = False

        # Get full details so that payload includes Real Feel
        params = {'details': 'true'}

        if self.unit_type == 'metric':
            params['metric'] = 'true'
        else:
            params['metric'] = 'false'

        response, response_status_code = self._make_request(end_point, self._headers, params)

        if response_status_code != requests.codes.ok: # pylint: disable=no-member
            new_refresh = datetime.now() + timedelta(hours=1)
            log.error(f'Hourly Forecast request failed. Setting next refresh for {new_refresh}.')
            self.hourly_forecasts.next_refresh = new_refresh
        else:
            # Loop through all forecast items, adding them to a list
            new_forecasts = []
            log.debug(f'Parsing {len(response)} elements...')
            for item in response:
                forecast_date = item['DateTime']
                precipitation_type = item.get('PrecipitationType', None)
                precipitation_icon = self._precip_icon_map.get(str(precipitation_type).lower(), '\uf084')

                new_item = ForecastData(
                    forecast_datetime= datetime.strptime(forecast_date, '%Y-%m-%dT%H:%M:%S%z')
                    , current_temperature= item['Temperature']['Value']
                    , feels_like_temperature= item['RealFeelTemperature']['Value']
                    , weather_icon_raw = item['WeatherIcon']
                    , weather_icon= self._weather_icon_map[item['WeatherIcon']]
                    , weather_text= item['IconPhrase']
                    , relative_humidity= item['RelativeHumidity']

                    , precipitation_type= precipitation_type
                    , precipitation_icon= precipitation_icon
                    , precipitation_probability= item['PrecipitationProbability']
                    , precipitation_amount=item['TotalLiquid']['Value']
                )

                new_forecasts.append(new_item)

            forecast_collection = ForecastDataCollection(
                forecasts=new_forecasts
                # Set forecast refresh time to 1 hour from now
                , next_refresh= datetime.now() + timedelta(hours=1)
            )

            # If response doesn't match existing data, indicate that the forecast was updated
            # Always update the object so next_refresh is accurate
            if self.current_conditions != forecast_collection:
                forecast_updated = True

            self.hourly_forecasts = forecast_collection

        log.debug('Exiting _get_hourly_forecast()')
        return forecast_updated

    def _get_daily_forecast(self):
        '''
        https://www.developer.accuweather.com/accuweather-forecast-api/apis/get/forecasts/v1/daily/5day/{locationKey}

            Hits the 10 day forecast end point with the provided location_id
            and returns the response payload

            Returns whether or not anything changed
        '''
        log.debug('Entering _get_daily_forecast()')

        end_point = f'forecasts/v1/daily/5day/{self._location_key}'
        forecast_updated = False

        # Get full details so that payload includes Real Feel
        params = {'details': 'true'}

        if self.unit_type == 'metric':
            params['metric'] = 'true'
        else:
            params['metric'] = 'false'

        response, response_status_code = self._make_request(end_point, self._headers, params)

        if response_status_code != requests.codes.ok: # pylint: disable=no-member
            new_refresh = datetime.now() + timedelta(hours=1)
            log.error(f'Daily Forecast request failed. Setting next refresh for {new_refresh}.')
            self.daily_forecasts.next_refresh = new_refresh
        else:
            # Loop through all forecast items, adding them to a list
            new_forecasts = []

            log.debug(f"Parsing {len(response['DailyForecasts'])} elements...")
            for item in response['DailyForecasts']:
                forecast_date = item['Date']
                forecast_datetime = datetime.strptime(forecast_date, '%Y-%m-%dT%H:%M:%S%z')

                day_precipitation_type = item['Day'].get('PrecipitationType', None)
                day_precipitation_icon = self._precip_icon_map.get(str(day_precipitation_type).lower(), '\uf084')

                night_precipitation_type = item['Night'].get('PrecipitationType', None)
                night_precipitation_icon = self._precip_icon_map.get(str(night_precipitation_type).lower(), '\uf084')

                # Day
                day = ForecastData(
                    forecast_datetime= forecast_datetime
                    , is_nighttime_forecast= False
                    , high_temperature= item['Temperature']['Maximum']['Value']
                    , low_temperature= item['Temperature']['Minimum']['Value']
                    , feels_like_high = item['RealFeelTemperature']['Maximum']['Value']
                    , feels_like_low = item['RealFeelTemperature']['Minimum']['Value']

                    , precipitation_type= day_precipitation_type
                    , precipitation_icon= day_precipitation_icon
                    , precipitation_probability= item['Day']['PrecipitationProbability']
                    , precipitation_amount=item['Day']['TotalLiquid']['Value']

                    , weather_icon_raw = item['Day']['Icon']
                    , weather_icon= self._weather_icon_map[item['Day']['Icon']]
                    , weather_text= item['Day']['ShortPhrase']

                    , sunrise_time= datetime.strptime(item['Sun']['Rise'], '%Y-%m-%dT%H:%M:%S%z')
                    , sunset_time= datetime.strptime(item['Sun']['Set'], '%Y-%m-%dT%H:%M:%S%z')
                )

                # Night
                night = ForecastData(
                    forecast_datetime= forecast_datetime
                    , is_nighttime_forecast= True
                    , high_temperature= item['Temperature']['Maximum']['Value']
                    , low_temperature= item['Temperature']['Minimum']['Value']
                    , feels_like_high = item['RealFeelTemperature']['Maximum']['Value']
                    , feels_like_low = item['RealFeelTemperature']['Minimum']['Value']

                    , precipitation_type= night_precipitation_type
                    , precipitation_icon= night_precipitation_icon
                    , precipitation_probability= item['Night']['PrecipitationProbability']
                    , precipitation_amount=item['Night']['TotalLiquid']['Value']

                    , weather_icon_raw = item['Night']['Icon']
                    , weather_icon= self._weather_icon_map[item['Night']['Icon']]
                    , weather_text= item['Night']['ShortPhrase']

                    , sunrise_time= datetime.strptime(item['Sun']['Rise'], '%Y-%m-%dT%H:%M:%S%z')
                    , sunset_time= datetime.strptime(item['Sun']['Set'], '%Y-%m-%dT%H:%M:%S%z')
                )

                new_forecasts.append(day)
                new_forecasts.append(night)

            # Set next refresh to 6 am/pm, whichever comes first
            if datetime.now().hour > 6 and datetime.now().hour < 18:
                refresh_hour = 17
            else:
                refresh_hour = 5

            next_refresh = datetime.combine(date.today(), time(refresh_hour, 0))
            if next_refresh < datetime.now():
                next_refresh += timedelta(days=1)

            forecast_collection = ForecastDataCollection(
                forecasts= new_forecasts
                # Set forecast refresh time to 1 hour from now
                , next_refresh= next_refresh
            )

            # If response doesn't match existing data, indicate that the forecast was updated
            # Always update the object so next_refresh is accurate
            if self.current_conditions != forecast_collection:
                forecast_updated = True

            self.daily_forecasts = forecast_collection

        log.debug('Exiting _get_daily_forecast()')
        return forecast_updated

    def _get_needed_refresh_methods(self):
        '''
            Returns a list of all methods that need to be called to refresh object
            Method is included if it's within refresh_tolerance_mins
        '''
        log.debug('Entering _get_needed_refresh_methods()')

        update_methods_to_invoke = []

        adjusted_time = datetime.now() + timedelta(minutes= self.refresh_tolerance_mins)

        if adjusted_time > self.current_conditions.next_refresh:
            update_methods_to_invoke.append(self._get_current_conditions)

        if adjusted_time > self.hourly_forecasts.next_refresh:
            update_methods_to_invoke.append(self._get_hourly_forecast)

        if adjusted_time > self.daily_forecasts.next_refresh:
            update_methods_to_invoke.append(self._get_daily_forecast)

        if adjusted_time > self.alerts.next_refresh:
            update_methods_to_invoke.append(self._get_alerts)

        log.debug('Exiting _get_needed_refresh_methods()')

        return update_methods_to_invoke

    def refresh(self):
        '''
            Handles logic for determining if forecast needs to be refreshed
            and updating as needed

            Returns whether or not any forecast object has changed
        '''
        log.debug('Entering refresh()')

        has_changed = False

        update_methods_to_invoke = self._get_needed_refresh_methods()

        log.debug(f'update_methods_to_invoke has {len(update_methods_to_invoke)} items')
        for method in update_methods_to_invoke:
            has_changed_new = method()
            has_changed = has_changed or has_changed_new

        log.debug(f'Exiting refresh() with status {has_changed}')
        return has_changed