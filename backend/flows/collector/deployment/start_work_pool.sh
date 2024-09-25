#!/usr/bin/env sh
prefect work-pool create --type process work-pool-alpha
prefect work-pool ls
prefect worker start --pool work-pool-alpha

