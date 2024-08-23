# weather-dashboard #
A Python project for the Raspberry Pi that pushes weather forecast information and upcoming calendar events to an image or screen.

![image](https://user-images.githubusercontent.com/18541752/64130413-0edf2300-cd90-11e9-9d7b-71b1a9527c6b.png)

Features:
* Current Weather Conditions
* Daily Forecast
    * After 6pm, this will show the nightly forecast (if the service supports day/night forecasts)
    * If the service does not support day/night forecasts, tomorrow will be shown instead
* Hourly Forecasts (for the next 7 hours)
* Daily Forecasts (for the next 4 days)
* Weather Alerts
* Upcoming calendar events

Included calendar services:
* Google Calendar

Included forecast services:
* [AccuWeather](https://developer.accuweather.com/)
* [OpenWeather](https://openweathermap.org/api/one-call-3)

## Hardware ##
My project is running on a [Raspberry Pi Zero WH](https://www.adafruit.com/product/3708) (Zero W with GPIO headers), and a [7.5" monochrome Waveshare e-Paper screen](https://www.waveshare.com/product/mini-pc/raspberry-pi/displays/e-paper/7.5inch-e-paper-hat.htm). The screen has a fairly poor resolution, resulting it jagged text (as seen in the picture above).

## Getting Started ##

### Latitude / Longitude ###

The weather service calls use latitude / longitude to determine the forecast location. Lat/long coordinates can be obtained by dropping a marker on [Google Maps](https://www.google.com/maps). Paste your coordinates into app_config.ini, in the `[Global]` section, under `lat_long`.

### API Keys ###

Most services require an API key to retrive data. You will need to place your keys in the app_config.ini file.

For AccuWeather, sign up at https://www.developer.accuweather.com/. Paste the API Key in the `[AccuWeather]` section, under `api_key`.

**Note**: the free service only offers 50 API calls per day and multiple API calls are necessary to get the complete data set. Due to the limited number of API calls, I recommend using another service, such as DarkSky, when testing.

For OpenWeather, sign up at https://openweathermap.org/api/one-call-3. Paste the API Key in the `[OpenWeather]` section, under `api_key`. The service offers 1,000 free API calls a day, and a single API call provides every forecast element. The service requires a credit card on file, but you can also cap the daily nubmer of calls to 1,000 and avoid additional charges.

For Google Calendar access, you'll need to create a new Oauth Client ID at https://console.developers.google.com/apis/credentials/. Once the client ID has been created, you can click the download button to download a credentials.json file. Rename this to "gcal_credentials.json" and place it in the calendar_api folder.

Google requires OAuth to access data on your calendar. You will have to run the code on a computer with a screen, so that you can approve access. Once permission has been granted, you will not need to reapprove access (unless permission is revoked from your Google account). I approved the permission request on my Mac, before deploying to the monitor-less Pi.

### Time Zone ###
If a `time_zone` is included in the config file, the Google Calendar API will convert all events to this time zone. For a list of valid IANA time zone names, see [Wikipedia](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)

#### Pillow ####
This program uses the Pillow library to construct an image, which is then pushed to the screen. Follow the [Pillow installation instructions](https://pillow.readthedocs.io/en/stable/installation.html) for both the Python module, as well as the external libraries libjpeg and zlib

#### Waveshare e-Paper Screen ####
On your Pi, you'll need to follow all of the Waveshare instructions to get the demo code up and running. If you're not pushing to a Waveshare screen, you can leave the code in `DEBUG` mode, and the image will instead be pushed to a bitmap named dashboard.bmp. When in `DEBUG` mode, the Waveshare libraries are not needed.

### Creating a Service ###
The program should be registered as a service on the Pi, so that it runs continuously. One way of doing this is by following the instructions at https://www.raspberrypi.org/documentation/linux/usage/systemd.md

# Third Party Acknowledgements #
This project uses Google's [Roboto](https://fonts.google.com/specimen/Roboto?selection.family=Roboto) fonts, as well as Erik Flowers' [Weather Icons](https://erikflowers.github.io/weather-icons/) font.
