from analysis import *
import os
import pandas as pd

# Find CSV file
data_path = next((file for file in os.listdir('.') if file.endswith('.csv')), None) or ().throw(FileNotFoundError("No CSV file found in the current directory."))

display(f"Alphabot Log Report {data_path}")

# Load the data
df = pd.read_csv(data_path)
df['time'] = pd.to_datetime(df['thl_ts'], unit='us')
df.set_index('time', inplace=True)

# Run IMU analysis
imu_analysis = IMUAnalysis(df)
fig = imu_analysis.plot_imu_data()

# Show the plot
fig.show()

# Display summary statistics
display("IMU Data Summary")
display(imu_analysis.summarize_imu_data())
