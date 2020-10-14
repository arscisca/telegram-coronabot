import datetime

import pandas as pd
import numpy as np

import matplotlib
import matplotlib.dates
import matplotlib.pyplot as plt
import matplotlib.ticker

import tempfile

from urllib.error import HTTPError

import constants
import dateinterval

matplotlib.use('agg')
plt.style.use('dark_background')


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
        interval (DateInterval): date interval
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
        interval (DateInterval): date interval
        data (dict(str, numpy.ndarray): a dict mapping a stat name to its values.
    """

    def __init__(self, location, interval, data):
        """
        Initiate dataset
        Args:
            location (Location): location of the data
            interval (DateInterval): date interval
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
    dummy_interval = dateinterval.DateInterval(date, date)
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
