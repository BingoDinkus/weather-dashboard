'''
    All of the necessary classes to create a forecast,
    and a collection of forecasts.

    Used by WeatherForecast
'''

__author__ = 'Eric J. Harlan'
__license__ = "GPLv3"

from datetime import datetime

class Temperature():
    '''
        A simple class to make it easier to display rounded temperatures
        with a degree symbol
    '''
    def __init__(self, temperature = None):
        self.temperature = temperature

    def __eq__(self, right_operand):
        # Some services return temperatures that are hundreths of a
        # degree, even if the readings are only a few seconds apart
        # Truncate the temperatures for comparison
        if self.temperature is None and right_operand.temperature is None:
            return True

        if self.temperature is None or right_operand.temperature is None:
            return False

        return int(self.temperature) == int(right_operand.temperature)

    def display(self):
        if self.temperature is None:
            return '–'
        else:
            return  f'{str(round(self.temperature))}°'

class ForecastData():
    '''
        Class for storing specific weather for a datetime
    '''
    def __init__(self, forecast_datetime = None
                , is_nighttime_forecast = None
                , current_temperature = None
                , feels_like_temperature = None
                , weather_icon_raw = None
                , weather_icon = None
                , weather_text = None
                , relative_humidity = None
                , high_temperature = None
                , low_temperature = None
                , feels_like_high = None
                , feels_like_low = None
                , precipitation_type = None
                , precipitation_icon = None
                , precipitation_probability = None
                , precipitation_amount = None
                , sunrise_time = None
                , sunset_time = None):
        self.forecast_datetime = forecast_datetime
        self.is_nighttime_forecast = is_nighttime_forecast
        self.current_temperature = Temperature(current_temperature)
        self.feels_like_temperature = Temperature(feels_like_temperature)
        self.weather_icon_raw = weather_icon_raw
        self.weather_icon = weather_icon
        self.weather_text = weather_text
        self.relative_humidity = relative_humidity

        self.high_temperature = Temperature(high_temperature)
        self.low_temperature = Temperature(low_temperature)
        self.feels_like_high = Temperature(feels_like_high)
        self.feels_like_low = Temperature(feels_like_low)

        self.precipitation_type = precipitation_type
        self.precipitation_icon = precipitation_icon
        self.precipitation_probability = precipitation_probability
        self.precipitation_amount = precipitation_amount

        self.sunrise_time = sunrise_time
        self.sunset_time = sunset_time

    def __eq__(self, right_operand):
        '''
            Overload equality operation to not include refresh_time
            Otherwise two items will never be equal
        '''

        # Some services give the current forecast's time as the current time
        # See if the forecast snapshots are within an hour of each other
        if self.forecast_datetime is None or right_operand.forecast_datetime is None:
            forecast_seconds_diff = 9999
        else:
            forecast_seconds_diff = (right_operand.forecast_datetime - self.forecast_datetime).total_seconds()

        return (
            forecast_seconds_diff < 3600
            and self.is_nighttime_forecast == right_operand.is_nighttime_forecast
            and self.current_temperature == right_operand.current_temperature
            and self.feels_like_temperature == right_operand.feels_like_temperature
            and self.weather_icon_raw == right_operand.weather_icon_raw
            and self.weather_icon == right_operand.weather_icon
            and self.weather_text == right_operand.weather_text
            and self.relative_humidity == right_operand.relative_humidity

            and self.high_temperature == right_operand.high_temperature
            and self.low_temperature == right_operand.low_temperature
            and self.feels_like_high == right_operand.feels_like_high
            and self.feels_like_low == right_operand.feels_like_low

            and self.precipitation_type == right_operand.precipitation_type
            and self.precipitation_probability == right_operand.precipitation_probability
            and self.precipitation_amount == right_operand.precipitation_amount
        )

    def __repr__(self):
        precip_display = ''
        if self.precipitation_probability is not None:
            precip_display = f'{self.precipitation_probability}%'

        return (
            f'Forecast Date: {self.forecast_datetime}\n'
            f'Is Nighttime Forecast: {self.is_nighttime_forecast}\n'
            f'Current Temp: {self.current_temperature.temperature}\n'
            f'Feels Like: {self.feels_like_temperature.temperature}\n'
            # Terminal can't display fonts, use raw response
            f'Weather Icon: {self.weather_icon_raw}\n'
            f'Weather Text: {self.weather_text}\n'
            f'Relative Humidity: {self.relative_humidity}\n'
            f'High/Low: {self.high_temperature} / {self.low_temperature}\n'
            f'Precip. Probab: {precip_display}\n'
            f'Sunrise: {self.sunrise_time}\n'
            f'Sunset: {self.sunset_time}'
        )

class ForecastDataCollection():
    '''
        A collection of ForecastData objects
    '''

    def __init__(self, forecasts=[], next_refresh=datetime.min):
        self.forecasts = forecasts
        self.next_refresh = next_refresh

    def __eq__(self, right_operand):
        return self.forecasts == right_operand.forecasts