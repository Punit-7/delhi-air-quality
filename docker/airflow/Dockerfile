# Airflow, plus a second and separate Python environment for the pipeline.
# Keeping the two apart means pandas, Polars and dbt can never clash with
# the exact package versions Airflow needs for itself.
FROM apache/airflow:3.3.2-python3.12

USER root
RUN mkdir -p /opt/project/data /opt/pipeline-venv \
    && chown -R airflow:root /opt/project /opt/pipeline-venv

USER airflow
COPY requirements.txt /tmp/requirements.txt
RUN python -m venv /opt/pipeline-venv \
    && PIP_USER=false /opt/pipeline-venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt

# Lets "python -m airquality.pipeline" find the code mounted at /opt/project/src
ENV PYTHONPATH=/opt/project/src \
    DATA_DIR=/opt/project/data
