FROM prefecthq/prefect:3-python3.11

WORKDIR /app


RUN pip3 install minio pymongo pandas fastapi uvicorn

ENV PREFECT_API_URL=http://server:4200/api
ENV PREFECT_EXPERIMENTAL_ENABLE_EXTRA_RUNNER_ENDPOINTS=True
ENV PREFECT_RUNNER_SERVER_HOST=127.0.0.1
RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Download and install MinIO client
RUN wget https://dl.min.io/client/mc/release/linux-amd64/mc -O /usr/local/bin/mc \
    && chmod +x /usr/local/bin/mc


COPY . /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
