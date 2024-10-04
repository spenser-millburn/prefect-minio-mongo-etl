import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

class VerticalAnalysis:
    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df

    def plot_vertical_data(self):
        # Create a single figure with 6 rows and 2 columns for subplots
        fig = make_subplots(
            rows=6, cols=2,
            subplot_titles=(
                "X Position", "Z Position", "Roll", "Wheel Angle", "Current",
                "Context", "Wheel Stepper Current", "Wheel Stepper Position",
                "Wheel Flag", "Pinion Stepper Current", "Pinion Stepper Position", "Pinion Flag"
            )
        )

        # X Position
        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['dmc_traj_inst_target_position_x'], name="X Position"), row=1, col=1)

        # Z Position
        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['dmc_traj_inst_target_position_z'], name="Z Position"), row=1, col=2)

        # Roll
        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['dmc_pos_d_som_roll'], name="Roll"), row=2, col=1)

        # Wheel Angle
        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['dbla0_pos_act'], name="Wheel Angle"), row=2, col=2)

        # Current
        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['dbla0_trq_act'], name="Current"), row=3, col=1)

        # Context
        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['so_context'], name="Context"), row=3, col=2)

        # Wheel Stepper Current
        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['wo_cmd_current'], name="Wheel Stepper Current"), row=4, col=1)

        # Wheel Stepper Position
        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['wo_act_pos'], name="Wheel Stepper Position"), row=4, col=2)

        # Wheel Flag
        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['wo_extend_flag_status'], name="Wheel Flag"), row=5, col=1)

        # Pinion Stepper Current
        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['po_cmd_current'], name="Pinion Stepper Current"), row=5, col=2)

        # Pinion Stepper Position
        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['po_act_pos'], name="Pinion Stepper Position"), row=6, col=1)

        # Pinion Flag
        fig.add_trace(go.Scatter(x=self.df['thl_ts'], y=self.df['po_extend_flag_status'], name="Pinion Flag"), row=6, col=2)

        # Update layout with appropriate titles and axis labels
        fig.update_layout(
            height=2000,  # Adjust height as per requirement
            width=2000,  # Adjust width as per requirement
            title="Consolidated Vertical Analysis Data",
            template="plotly_dark",
            showlegend=False
        )
        fig.update_xaxes(title_text="Time")
        fig.update_yaxes(title_text="Values")

        for i in range(1, 8):  # Loop through all rows
            fig.update_xaxes(matches='x1', row=i, col=1)
            fig.update_xaxes(matches='x1', row=i, col=2)


        return [fig]
