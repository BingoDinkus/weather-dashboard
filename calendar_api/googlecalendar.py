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
import pickle
from pathlib import Path
from googleapiclient.discovery import build as gbuild
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request as gRequest

log = logging.getLogger(__name__)

# Upgrade the logging level of the discovery module
logging.getLogger('googleapiclient.discovery').setLevel(logging.ERROR)

class GoogleCalendar(CalendarAPI):
    '''
        A class derived from CalendarAPI that implements the Google Calendar API
    '''
    def __init__(self, calendar_service):
        CalendarAPI.__init__(self, calendar_service)

    def _get_credentials(self):
        '''
            Checks to see if pickle.token exists and is valid
            Opens browser for OAuth if needed, and saves credentials
            Returns credential object

            Almost an exact copy of the quickstart process
            https://developers.google.com/calendar/quickstart/python
        '''
        log.debug('Entering _get_credentials()')

        # If modifying these scopes, delete the file token.pickle.
        SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

        folder = Path(__file__).resolve().parent

        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the firsist
        # time.
        token_path = folder / 'token.pickle'

        if token_path.is_file():
            with open(token_path, 'rb') as token:
                log.debug('Token exists, opening file')
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                log.debug('Creds expired, refreshing token')
                creds.refresh(gRequest())
            else:
                log.debug('Token missing, running OAuth flow')
                credentials_path = folder / 'gcal_credentials.json'
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            log.debug('Dumping token into pickle file')
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)

        log.debug('Exiting _get_credentials()')
        return creds

    def _get_calender_ids(self, calendar_service):
        '''
            Gets a list of calendar ids on the account
            Returns a list of all calendar ids
        '''
        log.debug('Entering _get_calender_ids()')

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

        log.debug('Entering _get_calender_ids()')
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
        calendar_ids = self._get_calender_ids(calendar_service)

        # Call the Calendar API
        now = datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time

        gcalendar_items = []
        for cal in calendar_ids:
            #pylint: disable=no-member
            events_result = calendar_service.events().list(calendarId=cal
                                                , timeMin=now, maxResults=10
                                                , singleEvents=True
                                                , orderBy='startTime').execute()
            gcalendar_items.extend(events_result.get('items', []))

        events = []
        for item in gcalendar_items:
            # Exclude the "Happy birthday!" item
            # Especially since my birthday is also on a calendar shared with me
            if item['summary'] != 'Happy birthday!':
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

            new_calendar = GoogleCalendar(CalendarServices.GOOGLECALENDAR)
            for item in new_events:
                new_calendar.add_event(item)

            if self != new_calendar:
                has_changed = True
                for item in new_events:
                    self.add_event(item)

        self.next_refresh = datetime.now() + timedelta(minutes= 50)

        log.debug(f'Exiting refresh() with status: {has_changed}')
        return has_changed