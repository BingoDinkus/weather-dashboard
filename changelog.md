# v2.0.0: OpenWeather API and more
* Removed DarkSky API (due to service being discontinued)
* Added support for OpenWeather API to replace DarkSky
* Updated to work with Pillow 10.0 and Windows


# v1.04: Calendar Fix (2020-11-17)
* Fixed crash caused by calendar event not having a summary

# v1.03: Added Quiet Hours feature (2020-08-05)
* New Quiet Hours feature supresses updates during specified hours
* Fixed unhandled error when requests fail (for AccuWeather & DarkSky)

# v1.02: Debugging & Calendar Fix (2019-09-29)
* Renamed darkskyio to darksky (module & class)
* Additional debugging in AccuWeather & DarkSky modules
* Reworked refresh mechanism for AccuWeather
* Fixed Off-By-One-Error with multi-day calendar events
* Fixed bug preventing DarkSky alerts from being updated
* Fixed bug preventing NWS alerts from being displayed

# v1.01: Calendar Fixes (2019-09-04)
* Fixed issue with multi-day events being added incorrectly
* Multi-day events where the start/end date are all day now show correctly as "All Day"
* Added more breathing room for days with only 1 event and a single line title

# v1.0: Initial Relase (2019-09-02)