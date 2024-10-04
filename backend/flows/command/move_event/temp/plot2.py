import plotly.express as px
import pandas as pd

# Data from the request
data = {
    "timestamp": [
        "2024-08-12 18:15:36.128", "2024-08-12 18:15:42.698", "2024-08-12 18:15:48.168",
        "2024-08-12 18:16:01.469", "2024-08-12 18:16:05.325", "2024-08-12 18:16:12.328",
        "2024-08-12 18:16:15.466", "2024-08-12 18:16:21.678", "2024-08-12 18:16:28.466",
        "2024-08-12 18:16:37.693"
    ],
    "src": [
        "1.4:1.2:1.3:2.3", "1.4:1.2:2.6:2.3", "1.4:1.2:2.6:2.1",
        "1.4:1.2:1.1:2.1", "1.4:1.2:1.3:2.1", "1.4:1.2:1.3:1.3",
        "1.4:1.2:1.3:1.2", "1.4:1.2:1.1:1.2", "1.2:1.2:1.2:1.2",
        "1.2:9.2:1.2:1.2"
    ],
    "dest": [
        "1.4:1.2:2.6:2.3", "1.4:1.2:2.6:2.1", "1.4:1.2:1.1:2.1",
        "1.4:1.2:1.3:2.1", "1.4:1.2:1.3:1.3", "1.4:1.2:1.3:1.2",
        "1.4:1.2:1.1:1.2", "1.2:1.2:1.2:1.2", "1.2:9.2:1.2:1.2",
        "1.2:9.2:3.2:1.2"
    ],
    "status": [
        "Success", "Success", "Success",
        "Success", "Success", "Success",
        "Success", "Success", "Success",
        "Failure"
    ],
    "type": [
        "Horizontal", "Vertical", "Horizontal",
        "Horizontal", "Vertical", "Vertical",
        "Horizontal", "Horizontal", "Horizontal",
        "Vertical"
    ],
    "description": [
        "Rack-to-Rack Move", "Rack-to-Rack Move", "Rack-to-Rack Move",
        "Rack-to-Rack Move", "Rack-to-Rack Move", "Rack-to-Rack Move",
        "Rack-to-Rack Move", "Rack-to-Deck Move", "Deck-to-Deck Move",
        "Deck-to-Deck Move"
    ]
}

# Create a DataFrame
df = pd.DataFrame(data)

# Extract Z-minor value (last number in UCC) for y-axis height
df['z_src'] = df['src'].apply(lambda x: int(x.split(".")[-1]))  # Get the Z-minor from src
df['z_dest'] = df['dest'].apply(lambda x: int(x.split(".")[-1]))  # Get the Z-minor from dest

# Function to get move type with Z level (optional, if you still want to show it)
def get_move_type_with_z(row):
    z_src = row['src'].split(":")[-1]  # Get the last number as Z from src
    z_dest = row['dest'].split(":")[-1]  # Get the last number as Z from dest
    
    if row['type'] == 'Horizontal':
        return f"Horizontal_z{z_src}" if z_src == z_dest else f"Horizontal_z{z_src}-z{z_dest}"
    elif row['type'] == 'Vertical':
        return f"Vertical_z{z_src}" if z_src == z_dest else f"Vertical_z{z_src}-z{z_dest}"
    return row['type']

# Apply the function to each row
df['type_with_z'] = df.apply(get_move_type_with_z, axis=1)

# Create a Plotly scatter plot where the y-axis is the Z-minor value (height)
fig = px.scatter(df, x="timestamp", y="z_src", color="status", hover_data=["src", "dest", "description"], template='plotly_dark')

# Add annotations for each point
for i, row in df.iterrows():
    fig.add_annotation(
        x=row['timestamp'],
        y=row['z_src'],  # Z-minor value on the y-axis
        text=f"Src: {row['src']}<br>Dest: {row['dest']}<br>Status: {row['status']}<br>Description: {row['description']}",
        showarrow=True,
        arrowhead=1,
        yshift=10  # Adjust the position of annotations higher up
    )

# Update layout
fig.update_layout(
    title="Move Events with Z Height (Based on Last Number in UCC)",
    xaxis_title="Timestamp",
    yaxis_title="Z Height (Z-minor value from UCC)",
    legend_title="Status",
    #  width=2500,  # Set plot width
    height=400  # Set plot height
)

# Show the plot
fig.show()
