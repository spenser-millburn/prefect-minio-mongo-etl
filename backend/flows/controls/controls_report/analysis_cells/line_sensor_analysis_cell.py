from analysis import *
import os
import pandas as pd

# Find CSV file
data_path = next((file for file in os.listdir('.') if file.endswith('.csv')), None) or (_ for _ in ()).throw(FileNotFoundError("No CSV file found in the current directory."))

display(f"Alphabot Log Report {data_path}")

# Load the data
df = pd.read_csv(data_path)
df['time'] = pd.to_datetime(df['thl_ts'], unit='us')
df.set_index('time', inplace=True)

# Run Line Sensor analysis
line_sensor_analysis = LineSensorAnalysis(df)
figures = line_sensor_analysis.plot_line_sensor_data()

# Show the plots
for fig in figures:
    fig.show()
