import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

class IMUAnalysis:
    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df

    def plot_imu_data(self):
        fig = make_subplots(rows=3, cols=1, subplot_titles=("IMU Accelerometer", "IMU Gyroscope", "IMU Magnetic Field"))

        # Accelerometer data (x, y, z)
        fig.add_trace(go.Scatter(x=self.df.index, y=self.df['imu_mb_ax'], name='IMU Acc X'), row=1, col=1)
        fig.add_trace(go.Scatter(x=self.df.index, y=self.df['imu_mb_ay'], name='IMU Acc Y'), row=1, col=1)
        fig.add_trace(go.Scatter(x=self.df.index, y=self.df['imu_mb_az'], name='IMU Acc Z'), row=1, col=1)

        # Gyroscope data (gx, gy, gz)
        fig.add_trace(go.Scatter(x=self.df.index, y=self.df['imu_mb_gx'], name='IMU Gyro X'), row=2, col=1)
        fig.add_trace(go.Scatter(x=self.df.index, y=self.df['imu_mb_gy'], name='IMU Gyro Y'), row=2, col=1)
        fig.add_trace(go.Scatter(x=self.df.index, y=self.df['imu_mb_gz'], name='IMU Gyro Z'), row=2, col=1)

        # Magnetic field data (gx, gy, gz)
        fig.add_trace(go.Scatter(x=self.df.index, y=self.df['imu_bf_gx'], name='IMU Mag X'), row=3, col=1)
        fig.add_trace(go.Scatter(x=self.df.index, y=self.df['imu_bf_gy'], name='IMU Mag Y'), row=3, col=1)
        fig.add_trace(go.Scatter(x=self.df.index, y=self.df['imu_bf_gz'], name='IMU Mag Z'), row=3, col=1)

        fig.update_layout(height=800, width=1000, title_text="IMU Data", template="plotly_dark")
        return fig

    def summarize_imu_data(self):
        summary = self.df[['imu_mb_ax', 'imu_mb_ay', 'imu_mb_az', 'imu_mb_gx', 'imu_mb_gy', 'imu_mb_gz']].describe()
        return summary
