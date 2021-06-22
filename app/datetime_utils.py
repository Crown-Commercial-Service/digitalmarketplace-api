import pendulum
import six

from sqlalchemy import types

from datetime import tzinfo, timedelta, datetime


ZERO = timedelta(0)
HOUR = timedelta(hours=1)


# A UTC class.
class UTC(tzinfo):
    """UTC"""

    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO


utc = UTC()


def vanilla(pendulum_dt):
    x = pendulum_dt
    return datetime(
        x.year,
        x.month,
        x.day,
        x.hour,
        x.minute,
        x.second,
        x.microsecond,
        tzinfo=utc)


def naive(pendulum_dt):
    x = pendulum_dt
    return datetime(
        x.year,
        x.month,
        x.day,
        x.hour,
        x.minute,
        x.second,
        x.microsecond,
        tzinfo=None)


def is_textual(x):
    return isinstance(x, six.text_type) or isinstance(x, six.binary_type)


class DateTime(types.TypeDecorator):
    '''Modified datetime to incorporate pendulum.
    '''

    impl = types.DateTime

    def process_bind_param(self, value, dialect):
        if value is not None:
            if is_textual(value):
                return value
            dt_utc = pendulum.instance(value).in_timezone('UTC')
            return naive(dt_utc)

    def process_result_value(self, value, dialect):
        if value is not None:
            result = pendulum.instance(value)

            if value.tzinfo is not None:
                # remove timezone from timezone-aware fields
                offset_removed = vanilla(result)
                result = pendulum.instance(offset_removed)
            return result


def utcnow():
    return pendulum.now('UTC')


def localnow():
    return pendulum.now()


def parse_interval(x):
    count, unit = x.split(None, 1)
    count = int(count)
    if not unit.endswith('s'):
        unit = '{}s'.format(unit)

    spec = {unit: count}
    return pendulum.duration(**spec)


def parse_time_of_day(x):
    return pendulum.parse(x).time()


def combine_date_and_time(date, time, timezone='UTC'):
    naive = datetime.combine(date, time)
    return pendulum.instance(naive, tz=timezone)
