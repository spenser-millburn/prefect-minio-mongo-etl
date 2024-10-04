from analysis import *
import os
import pandas as pd

data_path = next((file for file in os.listdir('.') if file.endswith('.csv')), None) or (_ for _ in ()).throw(FileNotFoundError("No CSV file found in the current directory."))
display(f"Alphabot Log Report {data_path}")

# Load the data and run the analysis
relevel_analysis, figures = load_and_analyze(data_path)

for fig in figures:
    fig.show()

display("DMC Maneuvers")
display(relevel_analysis.get_events()[0:5])

display("Dataframe")
display(relevel_analysis.df)
