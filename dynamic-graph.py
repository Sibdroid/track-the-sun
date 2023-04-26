from suntime import *
import typing as t
import plotly.graph_objects as go
from datetime import datetime, timedelta
from math import pi, sin, cos
import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output


def time_to_theta(time: str) -> float:
    """Converts time in "%H:%M" format to degrees.

    Args:
        time (str).

    Returns:
        The degrees, represented as a float. One minute
        corresponds to 1/4 of a degree, an hour corresponds
        to 15 degrees.

    Examples:
        time_to_theta("12:00")
        >>> 180.0

        time_to_theta("09:25")
        >>> 141.25
    """
    time = datetime.strptime(time, "%H:%M")
    total_hours = time.hour+time.minute/60
    return (360 * total_hours / 24)


def get_values(sunrise: str,
               sunset: str) -> float:
    """Gets values for plotting the graph from sunrise and sunset.

    Args:
        sunrise (str). Provided in "%H:%M" format.
        sunset (str). Provided in "%H:%M" format.

    Returns:
        A list of three values, each represented as a float in [0, 1].
            The first piece of the chart, represents the time between the
            midnight and the sunrise.
            The second piece, represents the time between the
            sunrise and the sunset [=the day].
            The third piece, represents between the sunset and the midnight.
    Examples:
        get_values("06:00", "19:00")
        >>> [0.25, 0.541666..., 0.208333...7]

        get_values("08:13", "20:41")
        >>> [0.34236111..., 0.519444...5, 0.13819444...]
    """
    sunrise_value = time_to_theta(sunrise)/360
    sunset_value = time_to_theta(sunset)/360
    return [sunrise_value, abs(sunrise_value-sunset_value), 1-sunset_value]


def get_angles(sunrise: str,
               sunset: str,
               current: str) -> t.List[float]:
    """Gets angles for plotting the graph from sunrise and sunset.

    Args:
        sunrise (str). Provided in "%H:%M" format.
        sunset (str). Provided in "%H:%M" format.

    Returns:
        A list of four angles.
    """
    start_theta, end_theta = 0.0, 360.0
    sunrise_theta = time_to_theta(sunrise)
    sunset_theta = time_to_theta(sunset)
    current_theta = time_to_theta(current)
    return [start_theta, sunrise_theta, sunset_theta, end_theta, current_theta]


def add_circular_labels(fig: go.Figure,
                        positions: t.List[float],
                        labels: t.List[str],
                        font_size: float) -> go.Figure:
    """Adds circular labels to the figure.

    Args:
        fig (go.Figure).
        positions (t.List[float]).
        labels (t.List[str]).
        font_size (float): the size of the labels.

    Returns:
        The figure with the added labels.
    """
    fig.update_polars(
        angularaxis = dict(
            tickvals=positions,
            ticktext=labels,
            tickcolor="white",
            ticklen=10,
            rotation=90,
            direction='clockwise',
            gridcolor="rgba(0,0,0,0)",
            tickfont_size=font_size),
        radialaxis = dict(
            visible=False,
            range=[0, 1]))
    return fig


def draw_chart(fig: go.Figure,
               sunrise: str,
               sunset: str,
               current: str,
               sunrise_today: bool=True) -> go.Figure:
    """Draws a donut chart of the day length.

    Args:
        sunrise (str). Provided in "%H:%M" format.
        sunset (str). Provided in "%H:%M" format.
        current (str). Provided in "%H:%M" format.

    Returns:
        The figure with the drawn chart.
    """
    COLORS = ["#7D8491", "#DEB841", "#7D8491"]
    LABELS = ["night-sunrise", "day", "night-sunset"]
    if sunrise_today:
        LINE_LABELS = ["sunrise", "sunset", "current"]
    else:
        LINE_LABELS = ["next sunrise", "sunset", "current"]
    values = get_values(sunrise, sunset)
    all_angles = get_angles(sunrise, sunset, current)
    thetas, widths = [], []
    for i in range(len(all_angles)-1):
        thetas += [(all_angles[i] + all_angles[i+1]) / 2]
        widths += [abs(all_angles[i+1] - all_angles[i])]
    r_min, r_max = 0.7, 1
    for theta, width, label, color, value in zip(thetas, widths, LABELS,
                                                 COLORS, values):
        fig.add_trace(go.Barpolar(
            r=[r_max],
            theta=[theta],
            width=[width],
            base=[r_min],
            name=label,
            marker=dict(color=color),
            text=value,
            legendgroup=label))
        fig.add_trace(go.Scatterpolar(
            r=[(r_min+r_max)/2],
            theta=[theta],
            mode='text',
            text="",
            textfont=dict(color='rgb(50,50,50)'),
            showlegend=False,
            legendgroup=label))
    for theta, label in zip(all_angles[1:3] + [all_angles[-1]],
                            LINE_LABELS):
        fig.add_trace(go.Scatterpolar(
            r=[r_min, r_max],
            theta=[theta, theta],
            mode='lines',
            marker=dict(color='white'),
            showlegend=False))
    positions = all_angles[1:3] + [all_angles[-1]]
    labels = [f"{i}: {j}" for i, j in
              zip(LINE_LABELS, [sunrise, sunset, current])]
    fig.add_trace(go.Scatterpolar(r=[0.65]*24,
                                  theta=[i for i in range(0, 360, 15)],
                                  mode="markers",
                                  marker=dict(color="white")))
    fig = add_circular_labels(fig, positions, labels, 16)
    fig.update_layout(template="plotly_dark",
                      showlegend=False,
                      font_family="Roboto",
                      polar=dict(
                          radialaxis=dict(
                              range=[0, 1],
                              showticklabels=False,
                              ticks="")))
    return fig


def display_data(fig: go.Figure,
                 coordinates: t.List[int]) -> go.Figure():
    """Displays data for the current date, location, and offset.

    Args:
        fig (go.Figure).

    Returns:
        The figure with the charted data: the donut chart for the
        day length and the annotation for general data.
    """
    periods = get_time_periods(datetime.now())
    sun = Sun(*periods,
              *coordinates,
              get_offset())
    sunrise, sunset = sun.get_sun_times()
    current = datetime.strftime(datetime.now(), "%H:%M")
    text = sun.get_text()
    fig = draw_chart(fig, sunrise, sunset, current, sun.is_day)
    fig.add_annotation(text=text,
                       align="center",
                       showarrow=False,
                       x=0.5, y=0.5,
                       xref="paper",
                       yref="paper",
                       font={"size": 20})
    return fig
    
    
def main():
    coordinates = get_coordinates()
    fig = go.Figure()
    fig = display_data(fig, coordinates)
    app = dash.Dash(__name__)
    app.layout = html.Div([
        dcc.Interval(
             id="interval-component",
             interval=1000,
             n_intervals=0),
        dcc.Graph(id="graph",
                  style={"width": "200vh",
                         "height": "100vh"})])
    @app.callback(
        Output("graph", "figure"),
        [Input("interval-component", "n_intervals")])
    def streamFig(value,
                  fig=fig,
                  coordinates=coordinates):
        fig.data = []
        fig.layout = {}
        fig = display_data(fig, coordinates)
        return fig
    app.run_server()
    

if __name__ == "__main__":
    main()
    
