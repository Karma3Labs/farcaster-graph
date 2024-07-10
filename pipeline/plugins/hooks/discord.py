# copied from https://medium.com/@artur.aacs/airflow-send-alerts-with-discord-69f343dfa8dd
import re
from typing import Optional
from datetime import datetime

from airflow.models import Variable, TaskInstance
from discord_webhook import DiscordWebhook, DiscordEmbed
from hooks.common import convert_hostname

TI = TaskInstance

def send_alert_discord(context):
	# Get Task Instances variables
	last_task: Optional[TaskInstance] = context.get('task_instance')
	task_name = last_task.task_id
	dag_name = last_task.dag_id
	log_link = convert_hostname(last_task.log_url)
	execution_date = datetime.fromisoformat(str(context.get('execution_date')))

	# Extract reason for the exception
	# try:
	# 	error_message = str(context["exception"])
	# 	error_message = error_message[:1000] + (error_message[1000:] and '...')
	# 	str_start = re.escape("{'reason': ")
	# 	str_end = re.escape('"}.')
	# 	error_message = re.search('%s(.*)%s' % (str_start, str_end), error_message).group(1)
	# 	error_message = "{'reason': " + error_message + ',}'
	# except:
	# 	error_message = "Some error that cannot be extracted has occurred. Visit the logs!"

	print('Sending discord alert')

	# Send Alert
	webhook = DiscordWebhook(url=Variable.get("discord_webhook")) # Update variable name with your change
	print('execution_date', execution_date)
	embed = DiscordEmbed(title="Airflow Alert - Task has failed!", color='CC0000', url=log_link, timestamp=execution_date)
	embed.add_embed_field(name="DAG", value=dag_name, inline=True)
	embed.add_embed_field(name="PRIORITY", value="HIGH", inline=True)
	embed.add_embed_field(name="TASK", value=task_name, inline=False)
	embed.add_embed_field(name="ERROR", value=str(context["exception"]))
	webhook.add_embed(embed)
	response = webhook.execute()

	return response