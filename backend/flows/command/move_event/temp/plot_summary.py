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

# Create a Plotly scatter plot
fig = px.scatter(df, x="timestamp", y="type", color="status", hover_data=["src", "dest", "description"], template='plotly_dark')

# Add annotations for each point
for i, row in df.iterrows():
    fig.add_annotation(
        x=row['timestamp'],
        y=row['type'],
        text=f"Src: {row['src']}<br>Dest: {row['dest']}<br>Status: {row['status']}<br>Description: {row['description']}",
        showarrow=True,
        arrowhead=1,
        yshift=10  # Adjust the position of annotations higher up
    )

# Update layout
fig.update_layout(
    title="Move Events",
    xaxis_title="Timestamp",
    yaxis_title="Move Type",
    legend_title="Status",
    width=2000,  # Set plot width
    height=300# Set plot height
)

# Show the plot
fig.show()
