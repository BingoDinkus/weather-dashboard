'''
    Contains a class for holding Weather Alerts,
    and a class for a collection of alerts.

    Used by WeatherForecast.
'''

__author__ = 'Eric J. Harlan'
__license__ = "GPLv3"

from datetime import datetime

class WeatherAlert():
    '''
        Class for storing weather alerts
    '''
    def __init__(self, title
                , regions
                , severity
                , description
                , effective_start
                , effective_end):
        self.title = title
        self.regions = regions
        self.severity = severity
        self.description = description
        self.effective_start = effective_start
        self.effective_end = effective_end

    def __eq__(self, right_operand):
        return (
            self.title == right_operand.title
            and self.regions == right_operand.regions
            and self.severity == right_operand.severity
            and self.description == right_operand.description
            and self.effective_start == right_operand.effective_start
            and self.effective_end == right_operand.effective_end
        )

    def __repr__(self):
        return (
            f'Title: {self.title}\n'
            f'Regions: {", ".join(self.regions)}\n'
            f'Severity: {self.severity}\n'
            f'Description: {self.description}\n'
            f'Effective: {self.effective_start} - {self.effective_end}'
        )

    def __str__(self):
        return f'{self.title} in effect from {self.effective_start} to {self.effective_end}.'

class WeatherAlertsCollection():
    '''
        A collection of WeatherAlert objects
    '''

    def __init__(self, alerts=[], next_refresh=datetime.min):
        self.alerts = alerts
        self.next_refresh = next_refresh

    def __eq__(self, right_operand):
        return self.alerts == right_operand.alerts

    def __repr__(self):
        return (
            f'{repr(self.alerts)}\n'
            f'Next Refresh: {self.next_refresh}'
        )