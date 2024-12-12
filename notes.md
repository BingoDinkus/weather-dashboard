# Shopping List:
* Raspberry Pi Zero WH (Zero W with Headers)
    * Adafruit: https://www.adafruit.com/product/3708
    * Case: https://www.adafruit.com/product/3252
* Screen:
    * Waveshare: https://www.waveshare.com/product/7.5inch-e-paper-hat.htm
    * Amazon: https://www.amazon.com/dp/B075R4QY3L
* Frame:
    * 5"x7" Deep Profile Metal Table Frame: https://www.target.com/p/5-34-x7-34-deep-profile-metal-table-frame-black-threshold-8482/-/A-88666767?preselect=88666767
* Velcro strips:
    * Command Narrow Picture Hanging Strips: https://www.target.com/p/command-narrow-picture-hanging-strips/-/A-81531976?preselect=81531976


# Setup notes
Weather.gov API user-agent:
https://www.weather.gov/documentation/services-web-api

Google needed:
    https://developers.google.com/calendar/api/quickstart/python
    get oauth json creds
        https://console.cloud.google.com/apis/credentials?project=weather-dashboard-250112

Waveshare setup:
    https://www.waveshare.com/wiki/7.5inch_e-Paper_HAT_Manual#Working_With_Raspberry_Pi
    Before installing lg library, `sudo apt install swig python3-dev python3-setuptools` (from https://github.com/gpiozero/lg)


# Raspberry Pi Setup

These steps were written using Raspian Lite ("Raspbian GNU/Linux 12 (bookworm)", 32-bit, released 2024-11-19) on a Pi Zero WH, and the included version of Python (Python 3.11.2).

1. Install Raspbian, or your choice OS
   - I used Raspbian Lite as a headless (no desktop) install. Make sure you set up Wi-Fi and enable SSH.
2. SSH into the Pi and update the system with the following commands:
   1. `sudo apt-get update`
   2. `sudo apt-get upgrade`
3. Setup your [Waveshare screen](https://www.waveshare.com/wiki/7.5inch_e-Paper_HAT_Manual#Working_With_Raspberry_Pi): This will vary from model to model. I've included the link and steps I followed for my Waveshare 7.5" v2 screen.
   1. Enable SPI
      1. `sudo raspi-config`
      2. Navigate to option "3) Interface Options"
      3. Navigate to option "I4) SPI"
      4. Select "Yes"
      5. Reboot the Pi with `sudo reboot`
      6. SSH back into your Pi again
   2. Install the lg library
      1. *Not in the Waveshare guide* Install python setuptools with `sudo apt install swig python3-dev python3-setuptools`
      2. `wget https://github.com/joan2937/lg/archive/master.zip`
      3. `unzip master.zip`
      4. `cd lg-master`
      5. `make`
      6. `sudo make install`
      7. Remove the install folder:
         1. `cd ..`
         2. `sudo rm -rf lg-master/`
         3. `sudo rm -f master.zip`
   3. Test the screen
      1. `sudo apt-get install python3-pip python3-pil python3-numpy`
      2. `git clone https://github.com/waveshare/e-Paper.git`
      3. `python3 e-Paper/RaspberryPi_JetsonNano/python/examples/epd_7in5_V2_test.py`
      4. *Optional:* Remove Python packages installed in step 1: `sudo apt-get remove python3-pip python3-pil python3-numpy`
4. Install git and clone the repo
   1. sudo apt-get install git`
   2. `git clone https://github.com/BingoDinkus/weather-dashboard.git`
5. Navigate into the repo and setup the virtual environment
   1. `cd weather-dashboard/`
   2. `python3 -m venv .venv`
   3. `source .venv/bin/activate`
   4. `python3 -m pip install --upgrade pip`
   5. `pip3 install google-api-python-client google-auth-httplib2 google-auth-oauthlib RPi.GPIO spidev gpiozero lgpio`
   6. Install Pillow
      1. `sudo apt-get install libjpeg-dev libfreetype6-dev zlib1g-dev libpng-dev`
      2. `pip3 install pillow`
6. Setup your Weather Dashboard
   1. Edit "app_config.toml" in the editor of your choice. You can create a copy of the sample config to get started.
      1. `cd ~/weather-dashboard/`
      2. `cp app_config.sample.toml app_config.toml`
      3. `nano app_config.toml`
      4. Update the config file with your API keys and change your settings as needed
   2. OAuth Permissions
      1. Grant OAuth permissions: OAuth is required to view personal calendars, service accounts cannot be used. If you have not already granted permission to your app, you will need to do this on a computer that has a web browser- this cannot be done on a headless Pi.
         -  Since I'm using a headless Pi, I used my regular desktop. This may require performing the above setup steps on an additional device. If anyone has a better way to handle this, please let me know. If you've already granted access, skip to 6.2.2 "Copy token file"
         1. Update the "app_config" file to enable debug mode `debug_mode = true`
         2. Run the script and allow it to complete. You should be able to open "dashboard.bmp" to see the output that would normally be drawn to your dashboard display
      2. Copy Token File
          -  The Google Calendar auth token can be copied from your regular desktop over to the Pi to allow OAuth access. I'm currently using Windows 11 with Windows Subsystem For Linux (WSL). Here are the steps I used to copy the file over
          1. Open the File Explorer and navigate to weather-dashboard\calendar_api
          2. Copy the "token.pickle" file and paste it into your Home directory in the Linux section (On the left bar: Linux > Ubuntu > Home > <user>)
          3. Open a Linux bash terminal and use the `scp` command to copy the file to the Pi: `scp ./token.pickle <user>@<host>:~/weather-dashboard/calendar_api`
   3. Test your Weather Dashboard
      1. ~/weather-dashboard/.venv/bin/python ~/weather-dashboard/main.py
   4. Cron

*Last Updated: 2024-12-11*