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
1. Install Raspbian, or your choice OS
   - I used Raspbian Lite as a headless (no desktop) install. Make sure you set up Wi-Fi and enable SSH.
2. SSH into the Pi and update the system with the following commands:
   1. `sudo apt-get update`
   2. `sudo apt-get upgrade`
3. Install git and clone the repo
   - `sudo apt-get install git`
   - `git clone https://github.com/BingoDinkus/weather-dashboard.git`
4. Navigate into the repo and setup the virtual environment
   - `cd weather-dashboard/`
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
   - `python3 -m pip install --upgrade pip`
   - `pip3 install google-api-python-client google-auth-httplib2 google-auth-oauthlib Pillow`
5. Setup your [Waveshare screen](https://www.waveshare.com/wiki/7.5inch_e-Paper_HAT_Manual#Working_With_Raspberry_Pi): This will vary from model to model. I've included the link and steps I followed for my Waveshare 7.5" v2 screen.
   1. Enable SPI
      1. `sudo raspi-config`
      2. Navigate to option "3) Interface Options"
      3. Navigate to option "I4) SPI"
      4. Select "Yes"
      5. Reboot the Pi with `sudo reboot`
      6. SSH into your Pi again
   2. Install the lg library
      1. *Not in the Waveshare guide* Install python setuptools with `sudo apt install swig python3-dev python3-setuptools`
      2. wget https://github.com/joan2937/lg/archive/master.zip
      3. unzip master.zip
      4. cd lg-master
      5. make
      6. sudo make install
      7. Remove the install folder:
         1. `cd ..`
         2. `sudo rm -rf lg-master/`
         3. `sudo rm -f master.zip`
   3. Test the screen
      1. `sudo apt-get install python3-pip python3-pil python3-numpy`
      2. `git clone https://github.com/waveshare/e-Paper.git`
      3. `python3 e-Paper/RaspberryPi_JetsonNano/python/examples/epd_7in5_V2_test.py`
6. Setup your Weather Dashboard config
   1. Edit "app_config.toml" in the editor of your choice. You can create a copy of the sample config to get started.
      1. `cd ~/weather-dashboard/`
      2. `cp app_config.sample.toml app_config.toml`
      3. `nano app_config.toml`
      4. Update the config file with your API keys and change your settings as needed
   2. Setup Pillow
      1. Install dependencies (taken from the Ubuntu section of the [Building From Source > External Libraries](https://hugovk-pillow.readthedocs.io/en/stable/installation.html#external-libraries) page, with some minor changes):
            ~~sudo apt-get install libtiff-dev libtiff5-dev libjpeg9-dev libopenjp2-7-dev zlib1g-dev
                libfreetype6-dev liblcms2-dev libwebp-dev tcl8.6-dev tk8.6-dev python3-tk
                libharfbuzz-dev libfribidi-dev libxcb1-dev~~~

                `sudo apt-get install libjpeg-dev libfreetype6-dev zlib1g-dev libpng-dev`
      2. `source .venv/bin/activate`
      3. `pip3 install Pillow`
      4. Test the script by running it in the venv: ` ~/weather-dashboard/.venv/bin/python3 ~/weather-dashboard/main.py`


sudo apt-get install libjpeg-dev libfreetype6-dev zlib1g-dev libpng-dev
pip install PIL --upgrade