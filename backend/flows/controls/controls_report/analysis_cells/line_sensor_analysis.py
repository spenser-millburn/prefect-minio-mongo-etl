import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

class LineSensorAnalysis:
    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df

    def plot_line_sensor_data(self):
        # Create a single figure with subplots
        fig = make_subplots(rows=3, cols=1, subplot_titles=("Line Sensor Offset", "Line Sensor Validity", "Line Sensor New Readings"))

        # Line Sensor Offset Plot
        fig.add_trace(go.Scatter(x=self.df.index, y=self.df["lsof_line"], name="Front"), row=1, col=1)
        fig.add_trace(go.Scatter(x=self.df.index, y=self.df["so_inp_front_sensor_filt"], name="F Filt"), row=1, col=1)
        fig.add_trace(go.Scatter(x=self.df.index, y=self.df["lsor_line"], name="Rear"), row=1, col=1)
        fig.add_trace(go.Scatter(x=self.df.index, y=self.df["so_inp_rear_sensor_filt"], name="R Filt"), row=1, col=1)

        # Line Sensor Validity Plot
        fig.add_trace(go.Scatter(x=self.df.index, y=self.df["lsof_line_valid"], name="Front"), row=2, col=1)
        fig.add_trace(go.Scatter(x=self.df.index, y=self.df["so_inp_front_sensor_filt_valid"], name="F Filt"), row=2, col=1)
        fig.add_trace(go.Scatter(x=self.df.index, y=self.df["lsor_line_valid"], name="Rear"), row=2, col=1)
        fig.add_trace(go.Scatter(x=self.df.index, y=self.df["so_inp_rear_sensor_filt_valid"], name="R Filt"), row=2, col=1)

        # Line Sensor New Readings Plot
        fig.add_trace(go.Scatter(x=self.df.index, y=self.df["lsof_new"], name="Front"), row=3, col=1)
        fig.add_trace(go.Scatter(x=self.df.index, y=self.df["lsor_new"], name="Rear"), row=3, col=1)

        # Update layout for the entire figure
        fig.update_layout(
            yaxis_title="Offset [m]",
            yaxis2_title="Valid [ ]",
            yaxis3_title="New [ ]",
            xaxis_title="Time",
            xaxis2_title="Time",
            xaxis3_title="Time",
            legend_title="Legend",
            template="plotly_dark",
            yaxis2=dict(tickmode="array", tickvals=[0, 1, 2], ticktext=["Inv", "Vld", "Int"])
        )

        return [fig]
