'''
    A class dervied from CalendarAPI.

    Handles the specific API calls to a Google Calendar.
'''

__author__ = 'Eric J. Harlan'
__license__ = "GPLv3"

from calendar_api.calendarevents import *
from calendar_api.calendarsapi import *

from datetime import datetime, date, time, timedelta
import logging
# import pickle
from pathlib import Path
from googleapiclient.discovery import build as gbuild
# from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2 import service_account
from google.auth.transport.requests import Request as gRequest

log = logging.getLogger(__name__)

# Upgrade the logging level of the discovery module
logging.getLogger('googleapiclient.discovery').setLevel(logging.ERROR)

class GoogleCalendar(CalendarAPI):
    '''
        A class derived from CalendarAPI that implements the Google Calendar API
    '''
    def __init__(self, time_zone):
        super().__init__(
            calendar_service= 'Google'
            , time_zone= time_zone
        )

    def _get_credentials(self):
        '''
            Creates credentials object from service account file
        '''
        log.debug('Entering _get_credentials()')

        # If modifying these scopes, delete the file token.pickle.
        SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

        folder = Path(__file__).resolve().parent

        log.debug('Reading secret file')
        service_account_file = folder / 'weather-dashboard-secret.json'

        log.debug('Creating credentials object')
        creds = service_account.Credentials.from_service_account_file(service_account_file, scopes=SCOPES)

        log.debug('Exiting _get_credentials()')
        return creds

    def _get_calendar_ids(self, calendar_service):
        '''
            Gets a list of calendar ids on the account
            Returns a list of all calendar ids
        '''
        log.debug('Entering _get_calendar_ids()')

        # Loop through all calendars to get their ids
        calendar_ids = []
        excluded_calendars = ('Contacts')
        page_token = None
        while True:
            #pylint: disable=no-member
            calendar_list = calendar_service.calendarList().list(pageToken=page_token).execute()
            for item in calendar_list['items']:
                if item['summary'] not in excluded_calendars:
                    calendar_ids.append(item['id'])
            page_token = calendar_list.get('nextPageToken')
            if not page_token:
                break

        log.debug('Entering _get_calendar_ids()')
        return calendar_ids

    def _get_events(self):
        '''
            Hits the Google Calendar (read-only) API and pulls the next 5 events
            from each calendar.

            Updates the events dictionary
        '''
        log.debug('Entering _get_events()')

        creds = self._get_credentials()
        calendar_service = gbuild('calendar', 'v3', credentials=creds
                                , cache_discovery=False)

        # Get all calendars ids
        calendar_ids = self._get_calendar_ids(calendar_service)

        # Call the Calendar API
        now = datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time

        gcalendar_items = []
        for cal in calendar_ids:
            #pylint: disable=no-member
            events_result = calendar_service.events().list(calendarId=cal
                                                , timeMin=now, maxResults=10
                                                , singleEvents=True
                                                , timeZone=self.time_zone
                                                , orderBy='startTime').execute()
            gcalendar_items.extend(events_result.get('items', []))

        events = []
        for item in gcalendar_items:
            # Exclude the "Happy birthday!" item
            # Especially since my birthday is also on a calendar shared with me
            if item.get('summary') and item.get('summary', '') != 'Happy birthday!':
                if not item['start'].get('dateTime'):
                    start_date_raw = item['start'].get('date')
                    end_date_raw = item['end'].get('date')

                    start_date = datetime.strptime(start_date_raw, '%Y-%m-%d')
                    end_date = datetime.strptime(end_date_raw, '%Y-%m-%d')

                    # For all day events, Google returns the day after
                    # Subtract a day to correct
                    end_date -= timedelta(days=1)
                    all_day_event = True
                else:
                    start_date_raw = item['start'].get('dateTime')
                    end_date_raw = item['end'].get('dateTime')

                    start_date = datetime.strptime(start_date_raw, '%Y-%m-%dT%H:%M:%S%z')
                    end_date = datetime.strptime(end_date_raw, '%Y-%m-%dT%H:%M:%S%z')

                    # TZ Conversion handed by Google, remove tzinfo so items can be sorted
                    start_date = start_date.replace(tzinfo=None)
                    end_date = end_date.replace(tzinfo=None)
                    all_day_event = False

                events.append(CalendarEvent(
                    event_name= item['summary']
                    , start_date= start_date
                    , end_date= end_date
                    , all_day_event= all_day_event
                    , multi_day_event= None
                ))

        # events.sort(key=lambda x: x.start_date)
        log.debug('Exiting _get_events()')
        return events

    def refresh(self):
        log.debug('Entering refresh()')

        has_changed = False

        if datetime.now() >= self.next_refresh:
            new_events = self._get_events()

            new_calendar = GoogleCalendar(self.time_zone)
            for item in new_events:
                new_calendar.add_event(item)

            if self != new_calendar:
                has_changed = True
                for item in new_events:
                    self.add_event(item)

        self.next_refresh = datetime.now() + timedelta(minutes= 50)

        log.debug(f'Exiting refresh() with status: {has_changed}')
        return has_changed