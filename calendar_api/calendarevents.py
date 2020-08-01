'''
    This class has the properties for a specific calendar event
'''

__author__ = 'Eric J. Harlan'
__license__ = "GPLv3"

class CalendarEvent():
    def __init__(self, event_name, start_date, end_date, all_day_event, multi_day_event):
        self.event_name = event_name
        self.start_date = start_date
        self.end_date = end_date
        self.all_day_event = all_day_event
        self.multi_day_event = multi_day_event

    def __eq__(self, right_operand):
        return (
            self.event_name == right_operand.event_name
            and self.start_date == right_operand.start_date
            and self.end_date == right_operand.end_date
            and self.all_day_event == right_operand.all_day_event
            and self.multi_day_event == right_operand.multi_day_event
        )

    def __repr__(self):
        return (
            f'Event Name: {self.event_name}\n'
            f'Start Date: {self.start_date}\n'
            f'End Date: {self.end_date}\n'
            f'All Day: {self.all_day_event}\n'
            f'Multi Day: {self.multi_day_event}'
        )

    def __str__(self):
        if self.all_day_event:
            return f'{self.event_name}: {self.start_date.date()}'
        elif self.end_date is None:
            return f'{self.event_name}: Starting at {self.start_date}'
        elif self.start_date is None:
            return f'{self.event_name}: Until {self.end_date}'
        else:
            return f'{self.event_name}: {self.start_date} - {self.end_date}'