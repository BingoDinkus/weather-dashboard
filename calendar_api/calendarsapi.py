'''
    An abstract base class for a calendar API server.
'''

__author__ = 'Eric J. Harlan'
__license__ = "GPLv3"

from abc import ABC, abstractmethod
from datetime import datetime, date, time, timedelta
from enum import Enum

from calendar_api.calendarevents import CalendarEvent

class CalendarServices(Enum):
    GOOGLECALENDAR = 1

class CalendarAPI(ABC):
    '''
        Base class for calendar API services
        Cannot be called `calendar` because Google code breaks
    '''
    def __init__(self, calendar_service):
        self.calendar_service = calendar_service
        self.events = {}
        self.next_refresh = datetime.min

    def __contains__(self, right_operand):
        '''
            Overload `in` operator, checks to see if a CalendarEvent
            is already on the calendar
        '''
        if not isinstance(right_operand, CalendarEvent):
            raise TypeError(f'Expected a CalendarEvent object, received {type(right_operand)}')

        for key, val in self.events.items():
            for item in val:
                if right_operand == item:
                    return True

        return False

    def __eq__(self, right_operand):
        return (
            self.calendar_service == right_operand.calendar_service
            and self.events == right_operand.events
        )

    def __getitem__(self, key):
        return self.events[key]

    def __iter__(self):
        # Iterate through events dictionary, sorting key (date) ascending
        for key, val in sorted(self.events.items(), key= lambda x: str(x[0])):
            # Sort the day's events
            val.sort(key= lambda x: (x.start_date, x.end_date))
            # Multi-day events in progress may include events from previous days
            # Exclude them
            if key >= datetime.now().date():
                yield key, val

    def __len__(self):
        total_events = 0
        for key, val in self.events.items():
            total_events += len(val)

        return total_events

    def keys(self):
        return self.events.keys()

    def items(self):
        return self.events.items()

    def values(self):
        return self.events.values()


    @staticmethod
    def calendar_days_duration(start_date, end_date):
        '''
            Returns the number of calendar days between start_date and end_date
        '''
        if not (isinstance(start_date, datetime) or isinstance(start_date, date)):
            raise TypeError(f'start_date: Expected date or datetime. Received {type(start_date)}')
        if not (isinstance(end_date, datetime) or isinstance(end_date, date)):
            raise TypeError(f'end_date: Expected date or datetime. Received {type(end_date)}')

        # Set start_date to a datetime with midnight as the time
        if isinstance(start_date, datetime):
            # Set start_date to midnight
            start_date = start_date.replace(hour = 0, minute = 0, second = 0, microsecond = 0)
        else:
            start_date = datetime.combine(start_date, time.min)

        if isinstance(end_date, datetime):
            # Set start_date to midnight
            end_date = end_date.replace(hour = 23, minute = 59, second = 59, microsecond = 0)
        else:
            end_date = datetime.combine(end_date, time.max)

        td = end_date - start_date

        return td.days + 1

    @staticmethod
    def date_range(start_date, end_date):
        '''
            Iterates through a range of dates, non-inclusive (like range())

            Parameters:
                start_date: The date or datetime to start at
                end_date: The date or datetime to end at (non-incluse)

            Returns:
                int: The counter (offset between start_date and the current date)
                date: The date in the range
        '''
        if not (isinstance(start_date, datetime) or isinstance(start_date, date)):
            raise TypeError(f'start_date: Expected date or datetime. Received {type(start_date)}')
        if not (isinstance(end_date, datetime) or isinstance(end_date, date)):
            raise TypeError(f'end_date: Expected date or datetime. Received {type(end_date)}')

        return_datetime = False
        if isinstance(start_date, datetime):
            start_date = start_date.date()
            return_datetime = True
        if isinstance(end_date, datetime):
            end_date = end_date.date()
            return_datetime = True

        for i in range((end_date - start_date).days):
            if return_datetime:
                yield i, datetime.combine(start_date + timedelta(days= i), time.min)
            else:
                yield i, start_date + timedelta(days= i)

    def _add_new_event(self, event_name, start_date, end_date, all_day_event):
        '''
            Creates a new CalendarEvent using the supplied parameters
            Splits multi-day events into separate events for each day
        '''
        duration_days = self.calendar_days_duration(start_date, end_date)

        # Google puts the end date as the next day for all day events
        # Giving us a duration of 1 day
        if duration_days < 2:
            # If the events dictionary doesn't have an entry for this date
            # create an empty list
            if start_date.date() not in self.events:
                self.events[start_date.date()] = []

            new_event = CalendarEvent(event_name, start_date, end_date
                                    , all_day_event, False)

            # Check to see if the event is already on the calendar
            # If not, add the event to the dictonary, using the start date as the key
            if new_event not in self:
                self.events[start_date.date()].append(new_event)
        else:
            # Loop through the days in the event, adding an event for each day
            for i, event_date in self.date_range(start_date, end_date + timedelta(days=1)):
                if event_date not in self.events:
                    self.events[event_date.date()] = []

                if event_date.date() == start_date.date():
                    if start_date.time() == time(0, 0):
                        event_start = event_date
                        event_end = event_date
                        all_day_event = True
                    else:
                        event_start = datetime.combine(event_date.date(), start_date.time())
                        event_end = None
                        all_day_event = False
                elif event_date.date() == end_date.date():
                    if end_date.time() == time(0, 0):
                        event_start = event_date
                        event_end = event_date
                        all_day_event = True
                    else:
                        event_start = None
                        event_end = datetime.combine(event_date.date(), end_date.time())
                        all_day_event = False
                else:
                    event_start = event_date
                    event_end = event_date
                    all_day_event = True

                new_event = CalendarEvent(
                                event_name= f'{event_name} (Day {i+1}/{duration_days})'
                                , start_date= event_start
                                , end_date= event_end
                                , all_day_event= all_day_event
                                , multi_day_event = True)

                # Check to see if the event is already on the calendar
                # If not, add the event to the dictonary, using the start date as the key
                if new_event not in self:
                    self.events[event_date.date()].append(new_event)

    def add_event(self, *args):
        '''
            Adds an event to the events dictionary

            Parameters: *args
                Option 1: A single CalendarEvent object
                Option 2: The properties for a new CalendarEvent object
                    event_name: The title of the event
                    start_date: The start datetime
                    end_date: The end datetime
                    all_day_event: Boolean for whether the event is an all day event
        '''
        if len(args) == 1 and type(args[0]) == CalendarEvent:
            self._add_new_event(
                                args[0].event_name
                                , args[0].start_date
                                , args[0].end_date
                                , args[0].all_day_event
            )
        elif len(args) == 4:
            self._add_new_event(
                                event_name= args[0]
                                , start_date= args[1]
                                , end_date= args[2]
                                , all_day_event= args[3]
            )
        else:
            raise TypeError('Expected either a CalendarEvent object, or the '
                            'properties for a new CalendarEvent object.')

    @abstractmethod
    def refresh(self):
        ''' To be implemented by derived class '''
        pass
