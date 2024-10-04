import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

class HorizontalAnalysis:
    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df

    def plot_horizontal_data(self):
        # Create the subplot figure with 7 rows, 2 columns
        fig = make_subplots(rows=7, cols=2, subplot_titles=[
            "X Position", "X Position Error", "X Velocity", "Yaw", "Z Position",
            "DMC Control Effort", "Differential Control Effort", "Wheel Angle",
            "Current", "DMC Maneuver", "Context", "Voltage", "FP Error"
        ])

        # Plot each graph in its respective row and column
        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['so_pos_som_x'], name="X Position"), row=1, col=1)
        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['dmc_err_som_x'], name="X Position Error"), row=1, col=2)
        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['dmc_vel_d_som_x'], name="X Velocity"), row=2, col=1)
        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['so_pos_som_yaw'], name="Yaw"), row=2, col=2)
        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['so_pos_som_z'], name="Z Position"), row=3, col=1)
        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['dmc_ctrl_eff_longitudinal_vel'], name="DMC Control Effort"), row=3, col=2)

        # Differential Control Effort
        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['dd_left_wheel_vel_cmd'], name="Left Wheel Command"), row=4, col=1)
        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['dd_right_wheel_vel_cmd'], name="Right Wheel Command"), row=4, col=1)

        # Wheel Angle
        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['dbla0_pos_act'], name="Left Wheel Angle"), row=4, col=2)
        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['dbla1_pos_act'], name="Right Wheel Angle"), row=4, col=2)

        # Current
        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['dbla0_trq_act'], name="Left Wheel Torque"), row=5, col=1)
        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['dbla1_trq_act'], name="Right Wheel Torque"), row=5, col=1)

        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['dmc_seg_maneuver'], name="DMC Maneuver"), row=5, col=2)
        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['so_context'], name="Context"), row=6, col=1)
        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['vo_inp_voltage'], name="Voltage"), row=6, col=2)
        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['fp_err_x'], name="FP Error"), row=7, col=1)

        # Update layout
        fig.update_layout(width=2000, height=2000, showlegend=True, template='plotly_dark')
        
        # Synchronize x-axes across all subplots
        for i in range(1, 8):  # Loop through all rows
            fig.update_xaxes(matches='x1', row=i, col=1)
            fig.update_xaxes(matches='x1', row=i, col=2)

        fig.update_xaxes(title_text="Time")
        fig.update_yaxes(title_text="Value")

        # return figure
        return [fig]

