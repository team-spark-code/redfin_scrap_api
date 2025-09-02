# HTTP 호출형
from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.http.operators.http import SimpleHttpOperator

# Airflow Connections에서 conn_id="rss_api" 로 http://rss-api:8030 같은 API 서버 등록
default_args = {"owner": "redfin", "retries": 1, "retry_delay": timedelta(minutes=2)}

with DAG(
    dag_id="rss_pipeline",
    default_args=default_args,
    start_date=datetime(2025, 9, 1),
    schedule="*/15 * * * *",
    catchup=False,
    tags=["rss"],
) as dag:

    init = SimpleHttpOperator(
        task_id="init",
        http_conn_id="rss_api",
        endpoint="/init",
        method="POST",
    )

    update = SimpleHttpOperator(
        task_id="update",
        http_conn_id="rss_api",
        endpoint="/update",
        method="POST",
    )

    discover = SimpleHttpOperator(
        task_id="discover",
        http_conn_id="rss_api",
        endpoint="/discover",
        method="POST",
        data='{"url":"https://techcrunch.com/tag/artificial-intelligence/","top_k":3}',
        headers={"Content-Type": "application/json"},
    )

    # 필요 시 stats를 파일로 저장하는 별도 서비스에서 호출하거나, 여기서 호출 후 XCom으로 넘겨도 됨
    init >> update >> discover
