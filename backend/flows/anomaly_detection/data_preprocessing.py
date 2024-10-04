from prefect import flow, task, get_run_logger

@task
def extract_data():
    logger = get_run_logger()
    data = "Sample data"
    logger.info(f"Extracted data: {data}")
    return data

@task
def transform_data(data):
    logger = get_run_logger()
    transformed_data = data.upper()
    logger.info(f"Transformed data: {transformed_data}")
    return transformed_data

@task
def load_data(data):
    logger = get_run_logger()
    logger.info(f"Loading data: {data}")
    # Simulate loading data
    logger.info("Data loaded successfully")

@flow
def etl_flow():
    logger = get_run_logger()
    logger.info("Starting ETL flow")
    data = extract_data()
    transformed_data = transform_data(data)
    load_data(transformed_data)
    logger.info("ETL flow completed")

if __name__ == "__main__":
    etl_flow()
