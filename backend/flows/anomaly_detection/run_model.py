import typer
import numpy as np
from joblib import load

app = typer.Typer()

@app.command()
def load_and_predict(
    model_path: str = typer.Argument(..., help="Path to the joblib model file"),
    data_points: int = typer.Option(10, help="Number of data points to generate for prediction"),
    mean: float = typer.Option(0.0, help="Mean of the normal distribution for generating data"),
    std_dev: float = typer.Option(1.0, help="Standard deviation of the normal distribution for generating data")
):
    """
    Load a trained model and use it for predictions on generated data.
    """
    # Load the model
    model = load(model_path)
    typer.echo(f"Model loaded from {model_path}")

    # Generate new data
    new_data = np.random.normal(mean, std_dev, (data_points, 2))
    typer.echo(f"Generated {data_points} new data points with mean={mean} and std_dev={std_dev}")

    # Make predictions
    predictions = model.predict(new_data)
    typer.echo(f"Predictions on new data: {predictions}")

if __name__ == "__main__":
    app()
