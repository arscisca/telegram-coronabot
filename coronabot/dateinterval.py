import datetime


class DateInterval:
    """Date interval
    Attributes:
        start (datetime.datetime): interval start date (included)
        end (datetime.datetime): interval end date (included)
    """

    def __init__(self, date_start, date_end):
        """Initialize interval
        Args:
            date_start (datetime.datetime): start date (included)
            date_end (datetime.datetime): end date (included)
        """

        # Always consider the start at 00:00:00 and push the end to 23:59:59
        def copy_date(d): return datetime.datetime(d.year, d.month, d.day)

        self.start = copy_date(date_start)
        self.end = copy_date(date_end) + datetime.timedelta(1, -1)

    def length(self):
        """Get the length of the interval
        Return:
            datetime.timedelta
        """
        return self.end - self.start

    def is_single_day(self):
        """Return True if the interval is composed of a single day
        Return:
            bool
        """
        return self.length() < datetime.timedelta(1)

    def __contains__(self, date):
        """Return True if date is contained in the interval.
        Args:
            date (datetime.datetime): date to check
        Return:
            bool
        """
        return (self.start <= date) and (date <= self.end)