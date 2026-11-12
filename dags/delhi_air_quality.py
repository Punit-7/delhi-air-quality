"""Hourly run: load the three sources side by side, then build and test the models.

Airflow only decides when things run and in what order. The work itself is the same
commands you ran by hand, so anything that fails here can be reproduced in a terminal.
"""

from datetime import datetime, timedelta

from airflow.providers.standard.operators.bash import BashOperator
from airflow.sdk import DAG

PIPELINE = "/opt/pipeline-venv/bin/python -m airquality.pipeline"
DBT = "/opt/pipeline-venv/bin/dbt"
DBT_DIR = "/opt/project/dbt"

with DAG(
    dag_id="delhi_air_quality",
    description="Extract, load, model and test Delhi air quality data",
    schedule="15 * * * *",  # a quarter past every hour, so stations have reported
    start_date=datetime(2026, 11, 1),
    catchup=False,  # do not replay every hour since start_date
    max_active_runs=1,  # never let two runs overlap
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5)},
    tags=["air-quality"],
) as dag:
    # Each job re-reads a little more than one hour. The overlap costs nothing
    # because loads are upserts, and it heals a run that was missed.
    load_air_quality = BashOperator(
        task_id="load_air_quality",
        bash_command=f"{PIPELINE} air-quality --hours 6",
    )
    load_weather = BashOperator(
        task_id="load_weather",
        bash_command=f"{PIPELINE} weather --days 2",
    )
    load_fires = BashOperator(
        task_id="load_fires",
        bash_command=f"{PIPELINE} fires --days 2",
    )

    # dbt build = run every model, then run every test on it, in dependency order.
    build_models = BashOperator(
        task_id="build_and_test_models",
        bash_command=f"{DBT} build --project-dir {DBT_DIR} --profiles-dir {DBT_DIR}",
    )

    [load_air_quality, load_weather, load_fires] >> build_models
