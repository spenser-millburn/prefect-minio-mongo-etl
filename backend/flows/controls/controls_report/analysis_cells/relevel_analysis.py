import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

class DMCAnalysis:
    def __init__(self) -> None:
        self.dmc_state = [
            "INVALID", "MOVE", "ORIENT", "SIT", "PRE_SIT",
            "REMOVE_BACKLASH", "RELEVEL_UP", "RELEVEL_DOWN", 
            "PARK_AT_CHANNEL", "PARK_AT_TOTE", "PARK_AT_FINE_POSITION",
            "PARK_AT_DOWN_SLOPE", "ENGAGE", "PREPARE_FOR_ENGAGE",
            "DESERVO_DRIVE_MOTORS", "ABORT", "DISABLE_BRIDGE_APPLY_BRAKES", 
            "INIT", "KILL", "MOVE_SUPER_S_CURVE_FORWARD", 
            "MOVE_SUPER_S_CURVE_REVERSE", "JOG_ANGULAR", 
            "HORIZONTAL_MODE", "VERTICAL_MODE", 
            "ROTATE_PINION_MODE", "MOVE_ON_PITCHED_DOWNSLOPE", 
            "MOVE_ON_PITCHED_UPSLOPE", "MAX_MANEUVER"
        ]

    def extract_state_windows(self, time_series) -> pd.DataFrame:
        windows = []
        current_state = None
        start_time = None

        for time, state in time_series.items():
            if current_state is None:
                current_state = state
                start_time = time
            elif state != current_state:
                windows.append(
                    {
                        "maneuver_label": self.dmc_state[current_state],
                        "maneuver_enum_value": current_state,
                        "start_time": start_time,
                        "end_time": time,
                    }
                )
                current_state = state
                start_time = time

        if start_time is not None:
            windows.append(
                {
                    "maneuver_enum_value": current_state,
                    "maneuver_label": self.dmc_state[current_state],
                    "start_time": start_time,
                    "end_time": time,
                }
            )

        return windows


class Analysis:
    def preprocess_from_csv(self, data_path: str) -> pd.DataFrame:
        df = pd.read_csv(data_path)
        df['time'] = pd.to_datetime(df['thl_ts'], unit="us")
        df.set_index('time', inplace=True)
        return df


class RelevelAnalysis(Analysis, DMCAnalysis):
    def __init__(self, data_path: str) -> None:
        Analysis.__init__(self)
        DMCAnalysis.__init__(self)
        self.data_path = data_path
        self.raw_df = self.preprocess_from_csv(data_path)
        self.df = self.raw_df.copy()
        self.event_windows = self.get_events()
        self.analyze()

    def analyze(self):
        self.df["dbla0_pos_err"] = (self.df["dbla0_pos_act"] - self.df["dbla0_pos_cmd"]).abs()
        self.df["dbla1_pos_err"] = (self.df["dbla1_pos_act"] - self.df["dbla1_pos_cmd"]).abs()

    def plot_relevel_events(self):
        relevel_events = [event for event in self.event_windows if "RELEVEL" in event["maneuver_label"]]
        figures = []  # Store all figures

        for i, event in enumerate(relevel_events):
            DF_CROP_OFFSET_START_SECONDS = 0
            DF_CROP_OFFSET_END_SECONDS = 0

            df = self.df.between_time(
                start_time=(event["start_time"] - pd.Timedelta(seconds=DF_CROP_OFFSET_START_SECONDS)).strftime('%H:%M:%S'),
                end_time=(event["end_time"] + pd.Timedelta(seconds=DF_CROP_OFFSET_END_SECONDS)).strftime('%H:%M:%S'))

            fig = make_subplots(rows=3, cols=2, subplot_titles=("Left Wheel Position", "Right Wheel Position", "Left Error", "Right Error", "Roll"))

            # Left Wheel Position
            fig.add_trace(go.Scatter(x=df.index, y=df["dbla0_pos_act"], name="dbla0_pos_act"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df["dbla0_pos_cmd"], name="dbla0_pos_cmd"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df["dbla0_pos_err"], name="dbla0_pos_err"), row=2, col=1)

            # Right Wheel Position
            fig.add_trace(go.Scatter(x=df.index, y=df["dbla1_pos_act"], name="dbla1_pos_act"), row=1, col=2)
            fig.add_trace(go.Scatter(x=df.index, y=df["dbla1_pos_cmd"], name="dbla1_pos_cmd"), row=1, col=2)
            fig.add_trace(go.Scatter(x=df.index, y=df["dbla1_pos_err"], name="dbla1_pos_err"), row=2, col=2)

            # Roll
            fig.add_trace(go.Scatter(x=df.index, y=df["dmc_pos_d_som_roll"], name="dmc_pos_d_som_roll"), row=3, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df["so_pos_som_roll"], name="so_pos_som_roll"), row=3, col=1)

            fig.update_layout(height=750, width=1000, title_text=f"Event {i + 1}: {event['maneuver_label']}", template="plotly_dark")
            figures.append(fig)

        return figures

    def get_events(self):
        time_series = pd.Series(self.raw_df["dmc_seg_maneuver"], index=self.raw_df.index)
        event_windows = self.extract_state_windows(time_series=time_series)
        return event_windows

def load_and_analyze(data_path):
    relevel_analysis = RelevelAnalysis(data_path)
    figures = relevel_analysis.plot_relevel_events()
    return relevel_analysis, figures
