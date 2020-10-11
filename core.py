import datetime
import dateparser

import pandas as pd
import numpy as np
import re

import matplotlib
import matplotlib.dates
import matplotlib.pyplot as plt
import matplotlib.ticker

import tempfile

from urllib.error import HTTPError

import constants

matplotlib.use('agg')
plt.style.use('dark_background')


class Location:
    def __init__(self, name, level):
        self.name = name
        self.level = level

    @staticmethod
    def resolve_alias(lname, aliases):
        """Map an aliased location name to its standard form.
        Args:
            lname (str): location name
            aliases (dict): a dictionary mapping each possible alias to the standard location name
        Return:
            str: standard location name. If location does not appear in `aliases` dict, it is returned unchanged.
        """
        if lname in aliases:
            return aliases[lname]
        return lname

    def __str__(self):
        """Convert to string"""
        return self.name.title()

    class LocationError(ValueError):
        """Exception for invalid locations"""
        pass


class Interval:
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


def download_csv_data(url, **kwargs):
    """Download data from a specified url.
    Args:
        url (str): url to an online .csv file
        **kwargs: arbitrary keyword arguments
    """
    return pd.read_csv(url, **kwargs)


def get_data_url(location, interval):
    """Get the url to the online .csv dataset from Protezione Civile based on the location and the interval of interest.
    Args:
        location (Location): location
        interval (Interval): date interval
    Return:
        str: url to the requested .csv document
    """
    url = "https://raw.githubusercontent.com/pcm-dpc/COVID-19/master/"
    if location.level == 'stato':
        url += "dati-andamento-nazionale/dpc-covid19-ita-andamento-nazionale"
    elif location.level == 'regione':
        url += "dati-regioni/dpc-covid19-ita-regioni"
    elif location.level == 'provincia':
        url += "dati-province/dpc-covid19-ita-province"
    else:
        raise ValueError("Invalid location")
    if interval.is_single_day():
        url += f"-{interval.start.year:0>4}{interval.start.month:0>2}{interval.start.day:0>2}"
    url += ".csv"
    return url


class InfectionDataset:
    """Dataset containing various stats on the infection status. All data is organized in parallel arrays aligned by
    date, which is mandatory in every dataset.
    Attributes:
        location (Location): location of the data
        interval (Interval): date interval
        data (dict(str, numpy.ndarray): a dict mapping a stat name to its values.
    """

    def __init__(self, location, interval, data):
        """
        Initiate dataset
        Args:
            location (Location): location of the data
            interval (Interval): date interval
            data (dict): a dict mapping a stat to its values over time.
        """
        self.location = location
        self.interval = interval
        if 'data' not in data:
            raise ValueError("Dataset has no associated dates")
        data_size = len(data['data'])
        if any(len(values) != data_size for values in data.values()):
            raise ValueError("Dataset data sizes are inconsistent")
        self.data = data

    @property
    def dates(self):
        """Show the dates array"""
        return self.data['data']

    @property
    def stats(self):
        """Return a list containing the available stats"""
        stats = set(self.data.keys()) - {'data'}
        return stats

    @classmethod
    def download(cls, location, interval, **kwargs):
        dataframe = download_csv_data(
            get_data_url(location, interval),
            converters={
                'data': datetime.datetime.fromisoformat
            },
            **kwargs
        )
        # Filter dataframe by date and location
        dataframe = dataframe[[date in interval for date in dataframe['data']]]
        if location.level == 'regione':
            dataframe = dataframe[dataframe['denominazione_regione'] == str(location)]
        elif location.level == 'provincia':
            dataframe = dataframe[dataframe['denominazione_provincia'] == str(location)]
        available_stats = set(dataframe.keys()) & set(constants.stats.keys())
        data = {'data': np.array(dataframe['data'])}
        for stat in available_stats:
            data[stat] = np.array(dataframe[stat])
        return cls(location, interval, data)

    def get_data(self, stat, interval):
        indices = np.where(date in interval for date in self.dates)
        return self[stat][indices]

    def __len__(self):
        return len(self.dates)

    def __getitem__(self, item):
        return self.data[item]

    def __setitem__(self, key, value):
        if len(value) != len(self):
            raise ValueError("Length of provided data does not match with dataset size.")
        self.data[key] = value


class Parser:
    """Abstract class for a generic Parser. Children classes must implement the methods `convert` and
    `mark_error`.
    Attributes:
        _result (any): conversion result, None by default
        status (bool): conversion status, True only if conversion was successful. If False, _result is not valid.
        error (str): error message associated to a failed conversion. Only valid if status is False.
    """

    def __init__(self):
        """Initialize Parser"""
        self._result = None
        self.status = False
        self.error = None

    @property
    def result(self):
        """Return conversion result only if status is true, otherwise raise an exception.
        Return:
            any: last conversion result
        Raise:
            Parser.ParserError: if status is false - some error occurred or conversion was never performed.
        """
        if self.status is True:
            return self._result
        else:
            raise Parser.ParserError("Cannot get results because an error occurred during conversion")

    def parse(self, string):
        """Parse a string using the convert and mark_error methods.
        Args:
            string (str): string to be parsed
        Return:
            bool: conversion status
        Raise:
            ParserError: if uncaught exceptions are raised
        """
        self.status = False
        try:
            result = self.convert(string)
        except Parser.ConversionError as e:
            self.status = False
            self.error = self.make_error_message(e, string)
        except Exception as e:
            self.status = False
            self.error = e.args
            raise Parser.ParserError(f"An error occurred during parsing") from e
        else:
            self._result = result
            self.status = True
        return self.status

    def convert(self, string):
        """Abstract method; must be overridden. Convert a string to its desired type or value.
        Args:
            string (str): string to be parsed, format is specific to the implemented
        Return:
            any
        """
        raise NotImplementedError()

    def make_error_message(self, error, string):
        """Generate the error message after a conversion failed and Parser.ConversionError was raised.
        Args:
            error (Parser.ConversionError): exception containing information about the error
            string (str): string that caused the error
        """
        raise NotImplementedError()

    def __bool__(self):
        """Mirror Parser status"""
        return self.status

    def __call__(self, *args, **kwargs):
        """Alias for `parse` method"""
        self.parse(*args, **kwargs)

    class ConversionError(Exception):
        """Exception for when the conversion fails for any reason"""
        pass

    class ParserError(Exception):
        """Exception for when, during conversion, other uncaught exceptions are raised"""
        pass


class ComposedParser(Parser):
    """Simplified interface for a nested parser.
    Attributes:
        subparsers (list): ordered list of Parser derived classes used to parse each field in a string
    """
    def __init__(self, subparsers):
        """Initialize instance
        Args:
            subparsers (list): ordered list of Parser derived classes used to parse each field in a string
        """
        super(ComposedParser, self).__init__()
        self.subparsers = subparsers

    def split(self, string):
        """Split composed string in a list of sub-strings. The size and the order of the returned list
        must correspond to the subparsers list.
        Args:
            string (str): string to split
        Return:
            list(str)
        """
        raise NotImplementedError()

    def convert(self, string):
        fields = self.split(string)
        if len(fields) != len(self.subparsers):
            raise Parser.ParserError(f"Cannot parse {len(fields)} fields with {len(self.subparsers)} parsers.")
        results = []
        for i, (field, parser) in enumerate(zip(fields, self.subparsers)):
            parser_instance = parser()
            partial_status = parser_instance.parse(field)
            if partial_status is False:
                raise Parser.ConversionError(i, field, parser_instance.error)
            results.append(parser_instance.result)
        return self.reduce(results)

    def reduce(self, partial_results):
        return partial_results

    def make_error_message(self, error, string):
        # Return the error message generated by the subparser that raised it
        return error.args[2]


class DateParser(Parser):
    """Date parser"""
    def convert(self, string):
        result = dateparser.parse(string, languages=['it', 'en'])
        if result is None:
            raise Parser.ConversionError(string)
        return result

    def make_error_message(self, error, string):
        return f"Non riconosco '{error.args[0]}' come una data valida. Prova ad utilizzare termini più semplici, " \
               f"come 'oggi', 'ieri', oppure insirisci la data per esteso come in '18 Luglio 2020'.\n\n" \
               f"Consulta /help per ulteriori informazioni."


class IntervalParser(ComposedParser):
    def __init__(self):
        super(IntervalParser, self).__init__([DateParser, DateParser])

    def split(self, string):
        _, interval, _ = re.split(f"({constants.interval})", string)
        _, sdate, edate, _ = re.split(fr"({constants.date})\s?-\s?({constants.date})", interval)
        return [sdate, edate]

    def reduce(self, partial_results):
        return Interval(*partial_results)


class LocationParser(Parser):
    def convert(self, string):
        string = Location.resolve_alias(string, constants.location_aliases)
        if string == constants.country:
            return Location(string, 'stato')
        elif string in constants.regions:
            return Location(string, 'regione')
        elif string in constants.provinces:
            return Location(string, 'provincia')
        else:
            raise Parser.ConversionError(string)

    def make_error_message(self, error, string):
        #TODO: suggest similar locations
        return f"Non riconosco '{string}' come un luogo valido. Prova con il nome di una provincia, di una regione o " \
               f"con 'Italia'.\n\nConsulta /help per ulteriori informazioni."


class StatParser(Parser):
    def convert(self, string):
        result = string.replace(' ', '_')
        if result not in constants.stats.keys():
            raise Parser.ConversionError(string)
        return string.replace(' ', '_')

    def make_error_message(self, error, string):
        return f"Non riconosco '{string}' come una statistica valida."


class ReportRequestParser(ComposedParser):
    REQUEST_PATTERN = constants.report_request

    def __init__(self):
        super(ReportRequestParser, self).__init__([LocationParser, DateParser])

    def split(self, string):
        _, location, date, _ = re.split(ReportRequestParser.REQUEST_PATTERN, string)
        if date is None:
            date = 'oggi'
        return location, date


class TrendRequestParser(ComposedParser):
    REQUEST_PATTERN = constants.trend_request

    def __init__(self):
        super(TrendRequestParser, self).__init__([StatParser, LocationParser, IntervalParser])

    def split(self, string):
        _, stat, location, interval, _ = re.split(TrendRequestParser.REQUEST_PATTERN, string)
        if location is None:
            location = 'italia'
        if interval is None:
            interval = '24/02/2020 - oggi'
        return stat, location, interval


def readable_number(num, thousands_sep="'"):
    """Convert number to string and format it in a human readable way
    Args:
        num (int, float): number
        thousands_sep (str): separator for the thousands
    Return:
        str: formatted number
    """
    return f"{num:,}".replace(',', thousands_sep)


def get_report(location, date):
    """Get a full report based on location and date.
    Args:
        location (Location): requested location
        date (datetime.datetime): requested date
    Return:
        str: full report with all available
    """
    dummy_interval = Interval(date, date)
    try:
        dataset = InfectionDataset.download(location, dummy_interval)
    except HTTPError:
        return f"Non ci sono dati per '{location}' in data {date.strftime('%d/%m/%Y')}. Prova con un'altra data, " \
               f"un altro luogo. Consulta il comando /help per ulteriori informazioni."
    report = f"*{location}* - {date.strftime('%d/%m/%Y')}:\n"
    for stat in sorted(dataset.stats):
        stat_name = stat.replace('_', ' ').capitalize()
        number = readable_number(dataset.get_data(stat, dummy_interval)[0])
        report += f"  _{stat_name}_: {number}\n"
    report += f"\nReport generato da {constants.bot_username}"
    return report


def plot_trend(stat, location, interval):
    dataset = InfectionDataset.download(location, interval)
    dates = dataset.dates
    if stat in dataset.stats:
        values = dataset[stat]
    else:
        raise KeyError(dataset.stats)
    return plot(dates, values, location=location, stat=stat.replace('_', ' '))


def plot(dates, values, **kwargs):
    # Create plot and style
    fig, ax = plt.subplots()
    style = stylize_plot(fig, ax, npoints=len(values), **kwargs)
    ax.plot_date(dates, values, **style)
    # Make temporary file
    temp_file = tempfile.NamedTemporaryFile(mode='w+b', prefix='plot-', suffix='.png', delete=True)
    plt.savefig(temp_file, bbox_inches='tight')
    temp_file.seek(0)
    return temp_file


def stylize_plot(fig, ax, **kwargs):
    """Add style to the plot
    Args:
        fig (matplotlib.pyplot.Figure): figure object
        ax (matplotlib.pyplot.Axes): axes object
        kwargs: arbitrary keyword arguments
    Return
        dict: keyword arguments to be used in plotting function
    """
    # Line style
    data_marker = '.' if kwargs.get('npoints', 14) < 14 else ''
    color = 'r'
    style = {'marker': data_marker, 'linestyle': '-', 'color': color}
    # Image style
    ax.grid(which='both', color='lightslategray')
    ax.get_xaxis().set_major_formatter(matplotlib.dates.ConciseDateFormatter(
        matplotlib.dates.AutoDateLocator()
    ))
    ax.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(
        lambda x, p: readable_number(x)
    ))
    # Labels and title
    xlabel = 'Data'
    ylabel = kwargs.get('stat', '???').capitalize()
    location = kwargs.get('location', '???')
    title = f"{location}: {ylabel}"
    ax.set_xlabel(xlabel, color='slateblue')
    ax.set_ylabel(ylabel, color='slateblue')
    ax.set_title(title)
    return style
