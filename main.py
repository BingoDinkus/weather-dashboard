#!/usr/bin/env python3

'''
    The core of the program
    Is responsible for creating forecast and calendar objects,
    refreshing items as needed, and redrawing the screen.
'''

__author__ = 'Eric J. Harlan'
__license__ = "GPLv3"

import forecast_api as f
import calendar_api as c
import display_controller as d

from datetime import datetime, timedelta
import drawinghelpers as dh
import logging
from logging.config import fileConfig
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import textwrap
import time
import tomllib
import os
import platform

# Consts
DEBUG = False

DAILY_DESCRIP_MAX_CHARS = 13
DAILY_DESCRIP_MAX_ROWS = 3

CALENDAR_TITLE_MAX_CHARS = 18
CALENDAR_TITLE_MAX_ROWS = 2

ALLOW_ALERTS_TO_OVERLAP = True

SCREEN_WIDTH = 640
SCREEN_HEIGHT = 480

# Library not available on dev computer
# Only import if not in debug mode
# if not DEBUG:
#     from wave_share import epd7in5_V2

# Set working directory to script location
os.chdir(Path(__file__).resolve().parent)

# Create logs directory if it's missing
Path('logs/').mkdir(exist_ok=True)

# Set up logger
logging_config_path = Path('logging_config.ini')
fileConfig(logging_config_path, disable_existing_loggers=False)
log = logging.getLogger()

# Alignment aliases
TOP = dh.VerticalAlignment.TOP
MIDDLE = dh.VerticalAlignment.MIDDLE
BOTTOM = dh.VerticalAlignment.BOTTOM

LEFT = dh.HorizontalAlignment.LEFT
CENTER = dh.HorizontalAlignment.CENTER
RIGHT = dh.HorizontalAlignment.RIGHT

# strf definitions
# In order to deal with inconsistent format defintions between Linux and Windows
if platform.system() == 'Windows':
    month_day = '%b %#d'
    hour_ampm = '%#I %p'
    hour_minute_ampm = '%#I:%M %p'
else:
    month_day = '%b %-d'
    hour_ampm = '%-I %p'
    hour_minute_ampm = '%-I:%M %p'

def main():
    log.info('Starting application...')

    # Read config file
    with open('app_config.toml', 'rb') as config_file:
        app_config = tomllib.load(config_file)

    global DEBUG
    DEBUG = app_config['global']['debug_mode']

    weather_provider = app_config['global']['weather_provider'].lower()
    display_controller = app_config['display']['display_controller'].lower()
    lat_long = app_config['global']['lat_long']
    quiet_hours = set(app_config['global'].get('quiet_hours', {}))
    time_zone = app_config['global'].get('time_zone')

    # Match units in config to UnitType enum
    config_unit = app_config['global'].get('unit_type', '').lower()

    if config_unit == 'metric':
        unit_type = f.UnitType.METRIC
    elif config_unit == 'imperial':
        unit_type = f.UnitType.IMPERIAL
    else:
        log.warn('Unit Type not specified or not supported. Defaulting to Imperial units.')
        unit_type = f.UnitType.IMPERIAL

    # Create forecast object
    if weather_provider == 'accuweather':
        # Create AccuWeather object
        forecast = f.AccuWeather(
            api_key= app_config['accuweather']['api_key']
            , unit_type= unit_type
            , lat_long= lat_long
            , time_zone = time_zone
            , nws_user_agent= app_config['nws']['user_agent']
        )
    elif weather_provider == 'openweather':
        # Create OpenWeather weather object
        forecast = f.OpenWeather(
            api_key= app_config['openweather']['api_key']
            , unit_type= unit_type
            , lat_long= lat_long
            , time_zone = time_zone
            , lang= app_config['openweather']['language']
        )
    else:
        raise AttributeError('Weather Provider not specified or not supported.')

    # Create display object
    if display_controller == 'waveshare_epaper':
        display = d.Waveshare_ePaper(model= app_config['display']['model'], debug_mode=DEBUG)
    else:
        raise AttributeError('Weather Provider not specified or not supported.')

    # Create Google Calendar object
    calendar = c.GoogleCalendar(c.CalendarServices.GOOGLECALENDAR, time_zone)

    run_application(display, forecast, calendar, quiet_hours)

    log.debug('Exiting application')

def run_application(display, forecast, calendar, quiet_hours):
    log.debug('Entering run_application()')

    # Create pathlib path to assets
    # Set up fonts
    assests_path = Path('assets/')
    fonts = {
        'Roboto' : {
            'Tiny': ImageFont.truetype(
                        str((assests_path / 'fonts/Roboto-Regular.ttf').absolute())
                        , 10)
            , 'Small': ImageFont.truetype(
                        str((assests_path / 'fonts/Roboto-Regular.ttf').absolute())
                        , 16)
            , 'Medium': ImageFont.truetype(
                        str((assests_path / 'fonts/Roboto-Regular.ttf').absolute())
                        , 24)
            , 'Large': ImageFont.truetype(
                        str((assests_path / 'fonts/Roboto-Regular.ttf').absolute())
                        , 32)
        }
        , 'RobotoBold' : {
            'Medium': ImageFont.truetype(
                        str((assests_path / 'fonts/Roboto-Bold.ttf').absolute())
                        , 24)
            , 'Large': ImageFont.truetype(
                        str((assests_path / 'fonts/Roboto-Bold.ttf').absolute())
                        , 32)
        }
        , 'Weather': {
            'Small': ImageFont.truetype(
                        str((assests_path / 'fonts/weathericons-regular-webfont.ttf').absolute())
                        , 14)
            , 'Medium': ImageFont.truetype(
                        str((assests_path / 'fonts/weathericons-regular-webfont.ttf').absolute())
                        , 22)
            , 'Large': ImageFont.truetype(
                        str((assests_path / 'fonts/weathericons-regular-webfont.ttf').absolute())
                        , 40)
        }
    }

    # Initialize
    next_refresh = datetime.min

    # Loop continuously, for app life-cycle
    while True:
        try:
            # Check to see if the current hour is a quiet hour
            if datetime.now().hour in quiet_hours:
                log.info(f'The current hour ({datetime.now().hour}:00) is a quiet hour. Sleeping for an hour.')

                # If next_refresh is initial value,
                # set it to the current time
                if next_refresh == datetime.min:
                    next_refresh = datetime.now()

                next_refresh = next_refresh + timedelta(hours= 1)
            else:
                # Invoke refresh method, store result to push screen refresh if needed
                screen_update_needed_forecast = forecast.refresh()
                log.debug(f'Calendar refresh exited with status: {screen_update_needed_forecast}')
                screen_update_needed_calendar = calendar.refresh()
                log.debug(f'Calendar refresh exited with status: {screen_update_needed_calendar}')

                screen_update_needed = screen_update_needed_forecast or screen_update_needed_calendar

                # Don't use calendar for next_refresh, just forecast
                next_refresh = forecast.get_next_refresh()
                log.debug(f'Next refresh: {next_refresh}')

                if forecast.api_calls_remaining < 1:
                    log.critical(f'All forecast API calls have been exhausted.')
                    screen_update_needed = False

                if screen_update_needed:
                    daily_forecasts = forecast.get_daytime_forecasts()

                    # Initialize image and canvas
                    # If it's after 6 pm, display tonight or tomorrow,
                    # depending on service's offerings
                    if datetime.now().hour >= 18:
                        if forecast.has_nighttime_forecasts:
                            img = Image.open(str((assests_path / 'images/background_tonight.bmp').absolute()))
                            top_right_panel_forecast = forecast.get_nighttime_forecasts()[0]
                            daily_forecasts = daily_forecasts[1:]
                        else:
                            img = Image.open(str((assests_path / 'images/background_tomorrow.bmp').absolute()))
                            top_right_panel_forecast = daily_forecasts[1]
                            daily_forecasts = daily_forecasts[2:]
                    else:
                        img = Image.open(str((assests_path / 'images/background_today.bmp').absolute()))
                        top_right_panel_forecast = daily_forecasts[0]
                        daily_forecasts = daily_forecasts[1:]
                    canvas = ImageDraw.Draw(img)

                    draw_now_panel(canvas, fonts, forecast.current_conditions.forecasts[0])
                    draw_top_right_panel(canvas, fonts, top_right_panel_forecast)
                    draw_hourly_panel(canvas, fonts, forecast.hourly_forecasts.forecasts)
                    draw_daily_panel(canvas, fonts, daily_forecasts)
                    draw_footer(canvas, fonts, forecast.weather_service_display_name)
                    if len(forecast.alerts.alerts) > 0:
                        draw_alerts(img, canvas, forecast.alerts.alerts[0], assests_path, fonts)
                    draw_upcoming_events(canvas, fonts, calendar)

                    # if DEBUG:
                    #     log.info('Pushing image to dashboard.bmp')
                    #     img.save('dashboard.bmp')
                    # else:
                    #     log.info('Initializing screen...')
                    #     epd = epd7in5_V2.EPD()
                    #     epd.init()
                    #     epd.Clear()

                    #     log.info('Updating screen...')
                    #     epd.display(epd.getbuffer(img))
                    #     time.sleep(2)

                    log.info('Pushing image to dashboard.bmp')
                    img.save('dashboard.bmp')
                    display.display_image(img)
                else:
                    log.info('Screen update not needed')

                next_refresh = forecast.get_next_refresh()

            # Determine how long to sleep
            sleep_needed_seconds = (next_refresh - datetime.now()).total_seconds()
            if sleep_needed_seconds < 0:
                log.warning(f'Sleep needed less than zero. Setting value to 0.')
                sleep_needed_seconds = 0

            log.info(f'Next refresh at {next_refresh}')
            log.info(f'Sleeping for {sleep_needed_seconds} seconds...')
            if DEBUG:
                # Don't loop endlessly in debug mode
                log.info('Debug mode, aborting app loop')
                break

            time.sleep(sleep_needed_seconds)
        except KeyboardInterrupt:
            log.info('Keyboard Interrupt detected. Exiting loop...')
            break
        # finally:
            # if not DEBUG:
            #     log.info('Sleeping display...')
            #     epd.sleep()

    log.debug('Exiting run_application()')

def draw_now_panel(canvas, fonts, forecast):
    log.debug('Entering draw_now_panel()')

    # Grid definition
    col_1_x = 26
    col_1_w = 62
    col_2_x = 88
    col_2_w = 75
    col_3_x = 163
    col_3_w = 40

    row_1_y = 10
    row_1_h = 18
    row_2_y = 28
    row_2_h = 41
    row_3_y = 69
    row_3_h = 18
    row_4_y = 87
    row_4_h = 18

    # Strings
    temperature_str = forecast.current_temperature.display()
    feels_like_temp_str = forecast.feels_like_temperature.display()
    humidity_str = f'{str(round(forecast.relative_humidity))}%'

    # Text objects
    weather_text = dh.Text(canvas, forecast.weather_text, fonts['Roboto']['Small'])
    icon = dh.Text(canvas, forecast.weather_icon, fonts['Weather']['Large'])
    temperature = dh.Text(canvas, temperature_str, fonts['RobotoBold']['Large'])
    feels_like_label = dh.Text(canvas, 'Feels Like:', fonts['Roboto']['Small'])
    feels_like_temp = dh.Text(canvas, feels_like_temp_str, fonts['Roboto']['Small'])
    humidity_label = dh.Text(canvas, 'Humidity:', fonts['Roboto']['Small'])
    humidity = dh.Text(canvas, humidity_str, fonts['Roboto']['Small'])

    # Coordinates
    weather_text_start = (col_1_x, row_1_y)
    weather_text_end = (col_1_x + col_1_w + col_2_w + col_3_w, row_1_y + row_1_h)

    icon_start = (col_1_x, row_2_y)
    icon_end = (col_1_x + col_1_w, row_2_y + row_2_h + row_3_h + row_4_h)

    temperature_start = (col_2_x, row_2_y)
    temperature_end = (col_2_x + col_2_w + col_3_w, row_2_y + row_2_h)

    feels_like_label_start = (col_2_x, row_3_y)
    feels_like_label_end = (col_2_x + col_2_w, row_3_y + row_3_h)

    feels_like_temp_start = (col_3_x, row_3_y)
    feels_like_temp_end = (col_3_x + col_3_w, row_3_y + row_3_h)

    humidity_label_start = (col_2_x, row_4_y)
    humidity_label_end = (col_2_x + col_2_w, row_4_y + row_4_h)

    humidity_start = (col_3_x, row_4_y)
    humidity_end = (col_3_x + col_3_w, row_4_y + row_4_h)

    # Write
    weather_text.write(weather_text_start, weather_text_end, LEFT, MIDDLE)
    icon.write(icon_start, icon_end, CENTER, MIDDLE)
    temperature.write(temperature_start, temperature_end, CENTER, MIDDLE)
    feels_like_label.write(feels_like_label_start, feels_like_label_end, LEFT, MIDDLE)
    feels_like_temp.write(feels_like_temp_start, feels_like_temp_end, LEFT, MIDDLE)
    humidity_label.write(humidity_label_start, humidity_label_end, LEFT, MIDDLE)
    humidity.write(humidity_start, humidity_end, LEFT, MIDDLE)

    log.debug('Exiting draw_now_panel()')

def draw_top_right_panel(canvas, fonts, forecast):
    log.debug('Entering draw_top_right_panel()')

    # Grid definition
    col_1_x = 208
    col_1_w = 62
    col_2_x = 270
    col_2_w = 80
    col_3_x = 350
    col_3_w = 80

    row_1_y = 10
    row_1_h = 18
    row_2_y = 28
    row_2_h = 41
    row_3_y = 69
    row_3_h = 18
    row_4_y = 87
    row_4_h = 18

    # Strings
    high_temp_str = forecast.high_temperature.display()
    low_temp_str = forecast.low_temperature.display()
    feels_like_high_str = forecast.feels_like_high.display()
    feels_like_low_str = forecast.feels_like_low.display()
    feels_like_str = f'Feels Like: {feels_like_high_str} / {feels_like_low_str}'
    precip_probability_str = f'{round(forecast.precipitation_probability)}%'
    if forecast.precipitation_amount is None:
        precip_amount_str = '–'
    else:
        precip_amount_str = f'{forecast.precipitation_amount}"'

    # Text objects
    # Ensure weather text isn't too long for cell
    weather_text_cell_width = col_1_w + col_2_w + col_3_w
    weather_text_str = forecast.weather_text
    while True:
        weather_text = dh.Text(canvas, weather_text_str, fonts['Roboto']['Small'])
        # If it fits, break the loop
        if weather_text.width <= weather_text_cell_width:
            break

        # Otherwise, remove another character and try again
        weather_text_str = weather_text_str[:-2] + '…'

    icon = dh.Text(canvas, forecast.weather_icon, fonts['Weather']['Large'])
    high_temp = dh.Text(canvas, high_temp_str, fonts['RobotoBold']['Large'])
    low_temp = dh.Text(canvas, f' / {low_temp_str}', fonts['Roboto']['Medium'])
    feels_like_temp = dh.Text(canvas, feels_like_str, fonts['Roboto']['Small'])
    precip_icon = dh.Text(canvas, str(forecast.precipitation_icon), fonts['Weather']['Small'])
    precip_probability = dh.Text(canvas, precip_probability_str, fonts['Roboto']['Small'])
    precip_amount_icon = dh.Text(canvas, '\uf04e', fonts['Weather']['Medium'])
    precip_amount = dh.Text(canvas, precip_amount_str, fonts['Roboto']['Small'])

    # Coordinates
    weather_text_start = (col_1_x, row_1_y)
    weather_text_end = (col_1_x + weather_text_cell_width, row_1_y + row_1_h)

    icon_start = (col_1_x, row_2_y)
    icon_end = (col_1_x + col_1_w, row_2_y + row_2_h + row_3_h + row_4_h)

    high_temp_start = (col_2_x, row_2_y)
    high_temp_end = (col_2_x + col_2_w, row_2_y + row_2_h)

    low_temp_start = (col_3_x, row_2_y)
    low_temp_end = (col_3_x + col_3_w, row_2_y + row_2_h)

    feels_like_temp_start = (col_2_x, row_3_y)
    feels_like_temp_end = (col_3_x + col_3_w, row_3_y + row_3_h)

    left_margin = 8
    icon_width = 30

    # Icon is lower set than expected and doesn't look centered. Move y up a little.
    precip_icon_start = (col_2_x + left_margin, row_4_y - 2)
    precip_icon_end = (col_2_x + icon_width + left_margin, row_4_y + row_4_h)

    precip_probability_start = (col_2_x + icon_width + left_margin, row_4_y)
    precip_probability_end = (col_2_x + col_2_w, row_4_y + row_4_h)

    # Icon is lower set than expected and doesn't look centered. Move y up a little.
    precip_amount_icon_start = (col_3_x + left_margin, row_4_y - 4)
    precip_amount_icon_end = (col_3_x + icon_width + left_margin, row_4_y + row_4_h)

    precip_amount_start = (col_3_x + icon_width + left_margin, row_4_y)
    precip_amount_end = (col_3_x + col_3_w, row_4_y + row_4_h)

    # Write
    weather_text.write(weather_text_start, weather_text_end, LEFT, MIDDLE)
    icon.write(icon_start, icon_end, CENTER, MIDDLE)
    high_temp.write(high_temp_start, high_temp_end, RIGHT, MIDDLE)
    low_temp.write(low_temp_start, low_temp_end, LEFT, MIDDLE)
    feels_like_temp.write(feels_like_temp_start, feels_like_temp_end, LEFT, MIDDLE)

    precip_icon.write(precip_icon_start, precip_icon_end, CENTER, TOP)
    precip_probability.write(precip_probability_start, precip_probability_end, LEFT, MIDDLE)

    precip_amount_icon.write(precip_amount_icon_start, precip_amount_icon_end, CENTER, TOP)
    precip_amount.write(precip_amount_start, precip_amount_end, LEFT, MIDDLE)

    log.debug('Exiting draw_top_right_panel()')

def draw_hourly_panel(canvas, fonts, forecast):
    log.debug('Entering draw_hourly_panel()')

    row_1_y = 108
    row_1_h = 18
    row_2_y = 126
    row_2_h = 30
    row_3_y = 156
    row_3_h = 18
    row_4_y = 174
    row_4_h = 18
    row_5_y = 192
    row_5_h = 18

    x = 64
    w = 48

    i = 0
    items_to_show = 7

    while i < items_to_show:
        item = forecast[i]

        # Strings
        hour_str = item.forecast_datetime.strftime(hour_ampm).lower()

        temperature_str = item.current_temperature.display()
        feels_like_str = item.feels_like_temperature.display()
        precip_probability_str = f'{round(item.precipitation_probability)}%'

        # Text objects
        hour = dh.Text(canvas, hour_str, fonts['Roboto']['Small'])
        icon = dh.Text(canvas, item.weather_icon, fonts['Weather']['Medium'])
        temperature = dh.Text(canvas, temperature_str, fonts['Roboto']['Small'])
        feels_like = dh.Text(canvas, feels_like_str, fonts['Roboto']['Small'])
        precip_probability = dh.Text(canvas, precip_probability_str, fonts['Roboto']['Small'])

        # Coordinates
        hour_start = (x, row_1_y)
        hour_end = (x + w, row_1_y + row_1_h)
        icon_start = (x, row_2_y)
        icon_end = (x + w, row_2_y + row_2_h)
        temperature_start = (x, row_3_y)
        temperature_end = (x + w, row_3_y + row_3_h)
        feels_like_start = (x, row_4_y)
        feels_like_end = (x + w, row_4_y + row_4_h)
        precip_probability_start = (x, row_5_y)
        precip_probability_end = (x + w, row_5_y + row_5_h)

        # Write
        hour.write(hour_start, hour_end, CENTER, MIDDLE)
        icon.write(icon_start, icon_end, CENTER, MIDDLE)
        temperature.write(temperature_start, temperature_end, CENTER, MIDDLE)
        feels_like.write(feels_like_start, feels_like_end, CENTER, MIDDLE)
        precip_probability.write(precip_probability_start, precip_probability_end, CENTER, MIDDLE)

        x += w + 5
        i += 1

    log.debug('Exiting draw_hourly_panel()')

def draw_daily_panel(canvas, fonts, forecast):
    log.debug('Entering draw_daily_panel()')

    row_1_y = 216
    row_1_h = 18
    row_2_y = 234
    row_2_h = 18
    row_3_y = 252
    row_3_h = 30
    row_4_y = 282
    row_4_h = 18
    row_5_y = 300
    row_5_h = 18

    x = 26
    w = 100

    i = 0
    items_to_show = min(4, len(forecast))

    while i < items_to_show:
        item = forecast[i]

        # Strings
        day_of_week_str = item.forecast_datetime.strftime('%A')
        date_str = item.forecast_datetime.strftime(month_day)

        high_temperature_str = item.high_temperature.display()
        low_temperature_str = item.low_temperature.display()
        temperature_str = f'{high_temperature_str} / {low_temperature_str}'

        precip_probability_str = f'{round(item.precipitation_probability)}%'

        # Text objects
        day_of_week = dh.Text(canvas, day_of_week_str, fonts['Roboto']['Small'])
        date = dh.Text(canvas, date_str, fonts['Roboto']['Small'])
        icon = dh.Text(canvas, item.weather_icon, fonts['Weather']['Medium'])
        temperature = dh.Text(canvas, temperature_str, fonts['Roboto']['Small'])
        # weather_text = dh.Text(canvas, weather_text_str, fonts['Roboto']['Small'])

        # Coordinates
        day_of_week_start = (x, row_1_y)
        day_of_week_end = (x + w, row_1_y + row_1_h)
        date_start = (x, row_2_y)
        date_end = (x + w, row_2_y + row_2_h)
        icon_start = (x, row_3_y)
        icon_end = (x + w, row_3_y + row_3_h)
        temperature_start = (x, row_4_y)
        temperature_end = (x + w, row_4_y + row_4_h)
        weather_text_start = (x, row_5_y)
        weather_text_end = (x + w, row_5_y + row_5_h)

        # Write
        day_of_week.write(day_of_week_start, day_of_week_end, CENTER, MIDDLE)
        date.write(date_start, date_end, CENTER, MIDDLE)
        icon.write(icon_start, icon_end, CENTER, MIDDLE)
        temperature.write(temperature_start, temperature_end, CENTER, MIDDLE)
        # weather_text.write(weather_text_start, weather_text_end, CENTER, MIDDLE)

        # Ensure text doesn't span more than 3 lines
        weather_text_str = item.weather_text
        while len(textwrap.wrap(weather_text_str, DAILY_DESCRIP_MAX_CHARS)) > DAILY_DESCRIP_MAX_ROWS:
            weather_text_str = weather_text_str[:-2] + '…'

        y = row_5_y
        for line in textwrap.wrap(weather_text_str, DAILY_DESCRIP_MAX_CHARS):
            text = dh.Text(canvas, line, fonts['Roboto']['Small'])
            text.write((x, y), (x + w, y + row_5_h), CENTER, MIDDLE)
            y += row_5_h

        x += w + 2
        i += 1

    log.debug('Exiting draw_daily_panel()')

def draw_footer(canvas, fonts, weather_service):
    log.debug('Entering draw_footer()')

    # Text objects
    last_update_str = (datetime.now().strftime(f'{month_day} at ')
                    + datetime.now().strftime(hour_minute_ampm).lower())
    last_update = dh.Text(canvas, f'Last updated on {last_update_str}', fonts['Roboto']['Tiny'])
    powered_by = dh.Text(canvas, f'Powered by {weather_service}', fonts['Roboto']['Tiny'])

    # Coordinates
    last_update_start = (10, SCREEN_HEIGHT - 15)
    last_update_end = (10 + last_update.width, SCREEN_HEIGHT - 15)

    powered_by_start = (SCREEN_WIDTH - powered_by.width - 10, SCREEN_HEIGHT - 15)
    powered_by_end = (SCREEN_WIDTH - 10, SCREEN_HEIGHT - 15)

    # Write
    last_update.write(last_update_start, last_update_end, LEFT, MIDDLE)
    powered_by.write(powered_by_start, powered_by_end, RIGHT, MIDDLE)

    log.debug('Exiting draw_footer()')

def draw_alerts(img, canvas, alert, assests_path, fonts):
    log.debug('Entering draw_alerts()')

    if ALLOW_ALERTS_TO_OVERLAP:
        max_alert_width = SCREEN_WIDTH - 20
    else:
        max_alert_width = 280

    # Text
    log.debug(f'Alert timeframe: {str(alert.effective_start)} - {str(alert.effective_end)}')
    if datetime.now() < alert.effective_start:
        preposition = 'beginning at'
        time = alert.effective_start
    else:
        preposition = 'until'
        time = alert.effective_end

    # Adjust alert text until it fits in allocated space
    alert_text = alert.title
    while True:
        alert_str = f"{alert_text} {preposition} {time.strftime(f'{month_day} {hour_minute_ampm}').lower()}"
        alert = dh.Text(canvas, alert_str, fonts['Roboto']['Small'])

        # If it fits, break the loop
        if alert.width <= max_alert_width:
            break

        alert_text = alert_text[:-2] + '…'

    # Load border edges
    img_border_edge_left = Image.open(assests_path / 'images/border_edge_left.bmp')
    img_border_edge_right = Image.open(assests_path / 'images/border_edge_right.bmp')

    # Coordinates
    background_start_x = int((SCREEN_WIDTH - alert.width) / 2)
    background_start_y = SCREEN_HEIGHT - 25

    # Centered, match start coords
    background_end_x = background_start_x + alert.width
    background_end_y = SCREEN_HEIGHT

    border_left_start = (background_start_x - img_border_edge_left.width
                        , background_start_y)

    border_right_start = (background_end_x
                        , background_start_y)

    alert_start_x = background_start_x
    alert_start_y = background_start_y + 2

    alert_end_x = background_end_x
    alert_end_y = background_end_y - 2

    # Draw background (rounded corners)
    canvas.rectangle((background_start_x, background_start_y, background_end_x
                    , background_end_y), fill=0)
    img.paste(img_border_edge_left, border_left_start)
    img.paste(img_border_edge_right, border_right_start)


    # Draw
    alert.write((alert_start_x, alert_start_y), (alert_end_x, alert_end_y)
                , CENTER, MIDDLE, fill='white')

    log.debug('Exiting draw_alerts()')

def draw_upcoming_events(canvas, fonts, calendar):
    log.debug('Entering draw_upcoming_events()')

    MAX_Y = 356
    date_padding = 4

    # Relative positions
    dow_start_x = 0
    dow_start_y = 0
    dow_end_x = 30
    dow_end_y = 14

    day_start_x = 0
    day_start_y = 16
    day_end_x = 30
    day_end_y = 44

    event_row_start_x = 35
    event_row_start_y = 0
    event_row_height = 18
    event_row_width = 143
    event_row_inner_padding = 1
    event_row_outer_pading = 10

    # Initial draw coordinates
    x_offset = 453
    y_offset = 27

    # Loop through calendar events until an event won't in allocated space
    # Loop through keys (dates)
    while True:
        line_coords = None
        for key, val in calendar:
            # Track whether the date has been drawn
            # So that we only draw it when we know
            # there's enough space for another event
            date_drawn = False

            for item_number, item in enumerate(val):
                event_rows = []
                events_remaining = len(val) - 1 - item_number

                # Ensure event title fits width and doesn't span too many rows
                title_str = item.event_name
                while len(textwrap.wrap(title_str, CALENDAR_TITLE_MAX_CHARS)) > CALENDAR_TITLE_MAX_ROWS:
                    title_str = title_str[:-2] + '…'

                total_event_height = 0
                for line in textwrap.wrap(title_str, CALENDAR_TITLE_MAX_CHARS):
                    new_line = dh.Text(canvas, line, fonts['Roboto']['Small'])
                    event_rows.append(new_line)
                    total_event_height += event_row_height + event_row_inner_padding

                # Create objects for time frame
                if item.all_day_event:
                    time_frame_str = 'All day'
                elif item.end_date is None:
                    time_frame_str = ('Starting at '
                                f'{item.start_date.strftime(hour_minute_ampm)[:-1].lower()}')
                elif item.start_date is None:
                    time_frame_str = ('Until '
                                f'{item.end_date.strftime(hour_minute_ampm)[:-1].lower()}')
                else:
                    time_frame_str = (f'{item.start_date.strftime(hour_minute_ampm)[:-1].lower()} - '
                                f'{item.end_date.strftime(hour_minute_ampm)[:-1].lower()}')

                time_frame = dh.Text(canvas, time_frame_str, fonts['Roboto']['Small'])
                event_rows.append(time_frame)

                ending_y = y_offset + total_event_height + time_frame.height
                if ending_y > MAX_Y:
                    # If we don't have room to write everything, exit
                    return

                if not date_drawn:
                    if line_coords:
                        canvas.line(line_coords, width=1)
                        y_offset += date_padding

                    # Output day of week and day
                    dow = dh.Text(canvas, key.strftime('%a'), fonts['Roboto']['Small'])
                    day = dh.Text(canvas, str(key.day), fonts['RobotoBold']['Medium'])

                    # Coordinates
                    dow_start = (dow_start_x + x_offset, dow_start_y + y_offset)
                    dow_end = (dow_end_x + x_offset, dow_end_y + y_offset)
                    day_start = (day_start_x + x_offset, day_start_y + y_offset)
                    day_end = (day_end_x + x_offset, day_end_y + y_offset)

                    dow.write(dow_start, dow_end, CENTER, TOP)
                    day.write(day_start, day_end, CENTER, TOP)
                    date_drawn = True

                # Output all lines in event title
                for line_number, line in enumerate(event_rows):
                    lines_remaining = len(event_rows) - 1 - line_number
                    line_start = (x_offset + event_row_start_x, y_offset)
                    line_end = (x_offset + event_row_start_x + event_row_width
                                , y_offset + event_row_height)
                    line.write(line_start, line_end, LEFT, MIDDLE)

                    if lines_remaining == 0:
                        if events_remaining == 0:
                            # Last line, but no more events on date
                            # Use padding between dates
                            y_offset += event_row_height + date_padding
                        else:
                            # Last line, but there are more events on this date
                            # Use event outer padding
                            y_offset += event_row_height + event_row_outer_pading
                    else:
                        # More lines for event, use event inner padding
                        y_offset += event_row_height + event_row_inner_padding

            # If the dow ends below the event, move the y coordinate down
            # to give proper padding between the bottom of the text
            # and the next row
            if day_end[1] > y_offset:
                y_offset += event_row_height - (dow_end_y - dow_start_y)

            # Draw line separating dates
            line_coords = (x_offset, y_offset, x_offset + 178, y_offset)

    log.debug('Exiting draw_upcoming_events()')

if __name__ == '__main__':
    try:
        main()
    except:
        log.exception('Exception caught at the top level')
        raise