from typing import Optional

from airflow.models import TaskInstance, Variable
from airflow.providers.pagerduty.hooks.pagerduty import PagerdutyHook
from airflow.providers.pagerduty.hooks.pagerduty_events import PagerdutyEventsHook
from airflow.providers.pagerduty.notifications.pagerduty import (
    send_pagerduty_notification,
)
from hooks.common import convert_hostname


# refer to https://github.com/astronomer/pagerduty_airflow_integration_benefits/blob/main/README.md
def send_alert_pagerduty(context):
    # Get Task Instances variables
    last_task: Optional[TaskInstance] = context.get("task_instance")
    log_link = convert_hostname(last_task.log_url)
    print("log_link", log_link)

    task_id = last_task.task_id
    dag_id = last_task.dag_id
    # pagerduty_default needs to be saved on Admin->Variable on the console with Pagerduty Events
    integration_key = Variable.get("pagerduty_default")

    print("Sending pagerduty alert")
    return PagerdutyEventsHook(integration_key).send_event(
        summary=f"Airflow Alert - {dag_id}-{task_id} failed",
        severity="critical",
        source=f"airflow dag_id: {dag_id}",
        dedup_key=f"{dag_id}-{task_id}",
        group=f"{dag_id}",
        component="airflow",
        class_type="Prod Data Pipeline",
        custom_details=str(context["exception"]),
        links=[{"href": log_link, "text": "Link to errored task log"}],
    )
