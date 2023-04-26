import typing as t
import geocoder
import time
from urllib3.exceptions import NewConnectionError
from datetime import date, datetime, timedelta
from math import *


def convert_trig(value: float,
                 deg_to_rad: bool=True) -> float:
    """Converts a value from degrees to radians or vice versa.

    Args:
        value (float).
        deg_to_rad (bool): whether to convert from degrees
        to radians or vice versa. Defaults to True [=the former].

    Return:
        The converted value, represented as a float.

    Examples:
        >>> convert_trig(45)
        0.7853981633974483

        >>> convert_trig(math.pi, False)
        180.0
    """
    if deg_to_rad:
        return value*pi/180
    return value*180/pi


def adjust_into_range(value: float,
                      value_range: range=range(0, 360)) -> float:
    """Adjusts a value into a given range.

    Args:
        value (float).
        value_range (range). Defaults to range(0, 360).

    Returns:
        The adjusted value.

    Examples:
        >>> adjust_into_range(380)
        20
        >>> adjust_into_range(-10)
        350
        >>> adjust_into_range(20, range(30, 120))
        140    
    """
    if value < value_range.start:
        return value+value_range.stop
    if value > value_range.stop:
        return value-value_range.stop
    return value


def time_to_datetime(time: float,
                     offset: float,
                     date: datetime) -> datetime:
    """Converts time to datetime object.

    Args:
        time (float).
        offset (float): the offset from the UTC.
        date (datetime).

    Returns:
        The datetime object, representing the date with the added time
        (including offset).

    Examples:
        >>> date_today = date.today() # datetime.date(2023, 4, 2)
        >>> time_to_datetime(4.2, 2, date_today)
        datetime.datetime(2023, 4, 2, 6, 12)

        >>> date_today = date.today() # datetime.date(2023, 4, 2)
        >>> time_to_datetime(9.5, -2, date_today)
        datetime.datetime(2023, 4, 2, 7, 30)
    """
    if time < 0:
        time += 24
    minutes, hours = modf(time)
    offset_minutes, offset_hours = modf(offset)
    hours += offset_hours
    minutes += offset_minutes
    hours = int(hours)
    minutes = int(round(minutes*60, 0))
    if minutes == 60:
        minutes = 0
        hours += 1
    if hours < 0:
        hours += 24
    if hours == 24:
        hours = 0
    if hours > 24:
        hours -= 24
    date_string = f"{date} {hours:02d}:{minutes:02d}"
    return datetime.strptime(date_string, "%Y-%m-%d %H:%M")


def format_time(time_: t.Union[datetime, float]) -> str:
    """Formats time to hours and minutes.

    Args:
        time_ (t.Union[datetime, float]): the time. Can either be a
        datetime object or a float.

    Returns:
        The time, formatted to hours and minutes. If the original
        argument was given as a negative float, it is adjusted
        into a 1440-minute [24-hour] range. If the time is None,
        returns an empty string.

    Examples:
        >>> format_time(768.0)
        '12:48'
        >>> date_today = datetime.strptime("2023-04-02 19:06:00",
                                           "%Y-%m-%d %H:%M:%S")
        >>> format_time(date_today)
        19:06
    """
    if time_ is None:
        return ""
    if isinstance(time_, float):
        if time_ < 0:
            time_ += 1440
        hours = int(time_ / 60)
        minutes = int(time_ % 60)
    else:
        hours = time_.hour
        minutes = time_.minute
    return f"{hours:02d}:{minutes:02d}"


class Sun:


    def __init__(self,
                 day: int,
                 month: int,
                 year: int,
                 latitude: int,
                 longitude: int,
                 offset: float,
                 date: datetime=date.today(),
                 zenith: t.Union[str, float]="official",
                 create_sun_tomorrow: bool=True) -> None:
        """Represents the Sun's position at given date (day, month, year)
        and location (latitude, longitude), with given offset from the UTC
        and zenith.

        Args:
            day (int).
            month (int).
            year (int).
            latitude (int), should be in [-180, 180].
            longitude (int), should be in [-90, 90].
            offset (float).
            date (datetime), defaults to date.today().
            zenith (t.Union[str, float]): the zenith, defaults to "official".
            If given as a str, four values are acceptable:
                "official": the most correct one, one minute late for sunrises
                            and precisely the correct time for sunsets. 
                "civil".
                "nautical".
                "astronomical".
            create_sun_tomorrow (bool). Whether the Sun object with
            tomorrow's date should be created. Used to prevent infinite loops.
            Defaults to True.

        Raises:
            ValueError: if latitude or longitude do not fit their bounds.
        """

        self.day = day
        self.month = month
        self.year = year
        if -90 <= latitude <= 90:
            self.latitude = latitude
        else:
            raise ValueError("Latitude should be in [-90, 90]")
        if -180 <= longitude <= 180:
            self.longitude = longitude
        else:
            raise ValueError("Longitude should be in [-180, 180]")
        self.offset = offset
        self.date = date
        self.zenith = {"official": 90.833333,
                       "civil": 96,
                       "nautical": 102,
                       "astronomical": 108}.get(zenith, zenith)
        self.now = datetime.now()
        self.is_day = self.sunrise() < self.now < self.sunset()
        today_midnight = self.now.replace(hour=0, minute=0, second=0,
                                          microsecond=0)
        conditions = [not self.is_day,
                      create_sun_tomorrow,
                      not today_midnight < self.now < self.sunrise()]
        if all(conditions):
            tomorrow = self.date+timedelta(days=1)
            self.sun_tomorrow = Sun(*get_time_periods(tomorrow),
                                    self.latitude, self.longitude, self.offset,
                                    tomorrow, self.zenith, False)
        else:
            self.sun_tomorrow = None
            

    def get_day_of_the_year(self) -> None:
        """Calculates the day of the year."""
        N1 = floor(275 * self.month / 9)
        N2 = floor((self.month + 9) / 12)
        N3 = (1 + floor((self.year - 4 * floor(self.year / 4) + 2) / 3))
        self.day_of_the_year = N1 - (N2 * N3) + self.day - 30


    def longitude_to_time(self,
                          is_sunrise: bool=True) -> None:
        """Calculates the time based on the longitude.

        Args:
            is_sunrise: whether the time should be calculated
            for the sunrise or the sunset, defaults to True [=the former].
        """
        self.longitude_hour = self.longitude / 15
        if is_sunrise:
            self.time = self.day_of_the_year + ((6 - self.longitude_hour) / 24)
        else:
            self.time = self.day_of_the_year + ((18 - self.longitude_hour) / 24)



    def calculate_time(self,
                       is_sunrise: bool=True) -> datetime:
        """Calculates the time of the sunrise or the sunset.

        Args:
            is_sunrise: whether the time should be calculated
            for the sunrise or the sunset, defaults to True [=the former].

        Returns:
            A datetime object, containing the desired time. 
        """
        self.get_day_of_the_year()
        self.longitude_to_time(is_sunrise)
        mean_anomaly = (0.9856 * self.time) - 3.289
        true_longitude = (mean_anomaly
                          + (1.916 * sin(convert_trig(mean_anomaly)))
                          + (0.020 * sin(convert_trig(2 * mean_anomaly)))
                          + 282.634)
        true_longitude = adjust_into_range(true_longitude)
        right_ascension = convert_trig(atan(0.91764 *
                                            tan(convert_trig(true_longitude))),
                                       False)
        right_ascension = adjust_into_range(right_ascension)
        longitude_quadrant = floor(true_longitude/90)*90
        right_ascension_quadrant = floor(right_ascension/90)*90
        right_ascension = (right_ascension + longitude_quadrant
                           - right_ascension_quadrant)
        right_ascension /= 15
        sin_declination = 0.39782 * sin(convert_trig(true_longitude))
        cos_declination = cos(convert_trig(convert_trig(sin_declination,
                                                        False)))
        local_hour_angle = ((cos(convert_trig(self.zenith))
                             - (sin_declination
                                * sin(convert_trig(self.latitude))))
                            / (cos_declination
                               * cos(convert_trig(self.latitude))))
        if is_sunrise:
            local_hour_angle = 360 - convert_trig(acos(local_hour_angle), False)
        else:
            local_hour_angle = convert_trig(acos(local_hour_angle), False)
        local_hour_angle /= 15
        time = (local_hour_angle + right_ascension
                - (0.06571 * self.time) - 6.622)
        utc_time = time - self.longitude_hour
        return time_to_datetime(utc_time, self.offset, self.date)
    

    def sunrise(self) -> datetime:
        """Calculates the time of the sunrise.

        Returns:
            A datetime object, containing the time of the sunrise.
        """
        return self.calculate_time()


    def sunset(self) -> datetime:
        """Calculates the time of the sunset.

        Returns:
            A datetime object, containing the time of the sunset.
        """        
        return self.calculate_time(False)


    def day_length(self) -> str:
        """Calculates the day length.

        Returns:
            The day length, formatted to hours and minutes.
        """
        minutes = (self.sunset()-self.sunrise()).total_seconds() / 60
        return f"Day length: {format_time(minutes)}"


    def time_to_sunrise(self,
                        now: datetime,
                        sunrise: datetime) -> str:
        """Calculates the time to the next sunrise.

        Args:
            now (datetime).
            sunrise (datetime).

        Returns:
            The time to the next sunrise, represented as a
            string of "%H:%M" format.
        """
        minutes = (sunrise-now).total_seconds() // 60
        return format_time(minutes)


    def time_to_sunset(self,
                       now: datetime,
                       sunset: datetime) -> str:
        """Calculates the time to the next sunset.

        Args:
            now (datetime).
            sunset (datetime).

        Returns:
            The time to the next sunset, represented as a
            string of "%H:%M" format.
        """        
        minutes = (sunset-now).total_seconds() // 60
        return format_time(minutes)


    def time_to_change(self) -> str:
        """Calculates the time to the next sunset or sunrise.

        Returns:
            If the next sunset is closer than the next sunrise,
            returns the time to the next sunset. Otherwise,
            returns the time to the next sunrise [=tomorrow's sunrise].
            Both times are represented in "%H:%M" format.
        """
        if self.is_day:
            return f"Sunset in: {self.time_to_sunset(self.now, self.sunset())}"
        elif self.sun_tomorrow is None:
            sunrise_tomorrow = self.sunrise()
        else:
            sunrise_tomorrow = self.sun_tomorrow.sunrise()
        return (f"Sunrise in: "
                f"{self.time_to_sunrise(self.now, sunrise_tomorrow)}")
        

    def get_sun_times(self) -> str:
        if self.sun_tomorrow is None:
            sunrise = self.sunrise()
        else:
            sunrise = self.sun_tomorrow.sunrise()
        return format_time(sunrise), format_time(self.sunset())


    def get_text(self) -> str:
        return (
            f"Now: {datetime.strftime(self.now, '%H:%M')} <br>"
            f"{self.day_length()} <br>"
            f"{self.time_to_change()}")
        

    def __str__(self) -> str:
        if self.sun_tomorrow is None:
            sunrise = self.sunrise()
        else:
            sunrise = self.sun_tomorrow.sunrise()
        return (
            f"Sunrise at: {sunrise.strftime('%H:%M')}\n"
            f"Sunset at: {format_time(self.sunset())}\n"
            f"{self.day_length()}\n"
            f"{self.time_to_change()}")        



    def __repr__(self) -> str:
        return (
            f"Sun({self.day}, {self.month}, {self.year}, "
            f"{self.longitude}, {self.latitude}, {self.offset}, "
            f"{self.date}, {self.zenith})")


def get_time_periods(date: datetime) -> t.List[int]:
    """Gets day, month and year from a date.

    Args:
        date (datetime).

    Returns:
        Day, month and year.
    """
    return [date.day, date.month, date.year]


def get_coordinates() -> t.List[float]:
    """Gets coordinates of the current location.

    Returns:
        The coordinates. Makes 5 attempts to get them 
        with 1-second delays.

    Examples:
        >>> get_coordinates() # Frankfurt am Main, Germany
        [50.1112, 8.6831]
        >>> get_coordinates() # Columbus, OH, United States
        [39.969, -83.0114]
    """
    for _ in range(5):
        try:
            return geocoder.ip("me").latlng
        except NewConnectionError:
            time.sleep(1)
            pass


def get_offset() -> float:
    """Gets the UTC offset of the current timezone.

    Returns:
        The UTC offset, in hours.

    Examples:
        >>> get_offset() # Yekaterinburg
        5.0
        >>> get_offset() # Berlin, summer
        2.0
        >>> get_offset() # Toronto, summer
        -5.0 
    """
        
    local_time = time.localtime()
    if local_time.tm_isdst:
        offset = -time.altzone
    else:
        offset = time.timezone
    return offset / 3600


def main() -> None:
    sun = Sun(*get_time_periods(datetime.now()),
              *[44.8125, 20.4612],
              get_offset())
    print(sun)


if __name__ == "__main__":
    main()
                                   
        
        
        
        
        
