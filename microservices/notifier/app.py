import os
import threading
import time
import boto3
import json
import logging
import requests
from datetime import datetime, timezone, timedelta

# Configuration Constants
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 300))
TEST_FLOW = os.getenv("TEST_FLOW", "false").lower() == "true"
CYBERARK_TABLE_NAME = os.getenv("CYBERARK_TABLE_NAME", "TestCyberArkIncidents" if TEST_FLOW else "CyberArkIncidents")
GITHUB_TABLE_NAME = os.getenv("GITHUB_TABLE_NAME", "TestGithubIncidents" if TEST_FLOW else "GithubIncidents")
TEST_CHANNEL = os.getenv("TEST_CHANNEL", "incident-testing")
PROD_CHANNEL = os.getenv("PROD_CHANNEL", "incident-alerts")
SLACK_CHANNEL = ""
SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN")
DEVOPS_MANAGER_PHONE = None
DIRECTOR_PHONE = None
# DynamoDB Setup
dynamodb = boto3.resource("dynamodb", region_name="us-west-2")
cyberark_table = dynamodb.Table(CYBERARK_TABLE_NAME)
github_table = dynamodb.Table(GITHUB_TABLE_NAME)
ESCALATION_ORDER = ["DEVOPS_MANAGER", "DIRECTOR"]

# SNS Setup
sns_client = boto3.client("sns", region_name="us-west-2")

# Logging Configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s")
logger = logging.getLogger(__name__)

# Escalation Timings (in seconds)
TIME_TO_ACKNOWLEDGE = int(os.getenv("TIME_TO_ACKNOWLEDGE", 600))
TIME_TO_CONCLUDE_ACTION = int(os.getenv("TIME_TO_CONCLUDE_ACTION", 1800))
TIME_TO_IMPLEMENT_ACTION = int(os.getenv("TIME_TO_IMPLEMENT_ACTION", 3600))
TIME_TO_CANCEL_NEXT_ESCALATION = int(os.getenv("TIME_TO_CANCEL_NEXT_ESCALATION", 900))

# Slack IDs
DEVOPS_ON_CALL = os.getenv("DEVOPS_ON_CALL", "devops_on_call")
DEVOPS_MANAGER_NICKNAME = os.getenv("DEVOPS_MANAGER", "devops_manager")
DIRECTOR_NICKNAME = os.getenv("RND_DIRECTOR", "rnd_director")


def get_secrets():
    """
    Fetch secrets from AWS Secrets Manager.
    """
    region_name = os.getenv("AWS_REGION", "us-west-2")  # Replace with your AWS region if needed

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)
    ret_dict = {}

    try:
        for secret_name in ["devops_manager_phone", "director_phone", "slack_app_bot_token", "devops_manager_nickname", "director_nickname"]:
            response = client.get_secret_value(SecretId=secret_name)
            secret_string = response.get("SecretString")
            if secret_string:
                secret_dict = json.loads(secret_string)  # Parse the JSON string into a dictionary
                ret_dict[secret_name] = list(secret_dict.values())[0]
    except Exception as e:
        logger.error(f"Failed to retrieve secret: {e}")
        raise
    return ret_dict


def get_incidents():
    """
    Fetch incidents with pending escalation stages.
    """
    try:
        new_incidents = []
        response = cyberark_table.scan()
        for cyberark_incident in response.get("Items", []):
            if cyberark_incident['incident_status'] != 'Resolved':
                new_incidents.append(cyberark_incident)
        return new_incidents
    except Exception as e:
        logger.error(f"Failed to fetch incidents: {e}")
        return []


def update_table_attribute(incident_id, attribute_value, attribute_name, update_table_name):
    """
    Update the slack_message_thread_ts attribute for a specific incident in the CyberArk table.

    Args:
        incident_id (str): The unique ID of the incident to update.
        attribute_value (str):
        attribute_name
        update_table_name

    Returns:
        dict: The response from the update operation.
    """
    table = cyberark_table
    if update_table_name != CYBERARK_TABLE_NAME:
        table = github_table
    try:
        # Perform the update
        response = table.update_item(
            Key={"incident_id": incident_id},  # Primary key to identify the record
            UpdateExpression=f"SET {attribute_name} = :val",
            ExpressionAttributeValues={":val": attribute_value},
            ReturnValues="UPDATED_NEW"  # Return the updated attributes
        )
        logger.info(f"Updated slack_message_thread_ts for incident_id {incident_id}: {response}")
        return response
    except Exception as e:
        logger.error(f"Failed to update incident {incident_id}: {e}")
        return None


def post_to_slack(text, subject=None, thread_ts=None, incident_id=None):
    """
    Post a message to Slack, either as a new message or as a reply in a thread.

    Args:
        text (str): The message text.
        subject (str, optional): The subject text for a new incident. Creates a new thread if provided.
        thread_ts (str, optional): The thread timestamp to reply in an existing thread. If None, a new message is created.
        incident_id (str, optional): The thread timestamp to reply in an existing thread. If None, a new message is created.

    Returns:
        dict: The response JSON from Slack if successful, or None on failure.
    """
    if not SLACK_API_TOKEN:
        logger.error("Slack API Token is not configured.")
        return None

    headers = {
        "Authorization": f"Bearer {SLACK_API_TOKEN}",
        "Content-Type": "application/json"
    }

    # If both subject and text are provided for a new incident:
    if subject and not thread_ts:
        # Post the subject as a new message
        payload = {
            "channel": SLACK_CHANNEL,
            "text": subject,  # Post subject as the main message
        }

        try:
            response = requests.post(
                url="https://slack.com/api/chat.postMessage",
                json=payload,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            slack_response = response.json()

            if slack_response.get("ok"):
                new_thread_ts = slack_response.get("ts")  # Get thread_ts for the new message
                logger.info(f"New thread created with subject: {subject}")
                update_table_attribute(incident_id=incident_id, attribute_value=new_thread_ts, attribute_name="slack_message_thread_ts", update_table_name=CYBERARK_TABLE_NAME)
                # Post the text as a reply in the thread
                if text:
                    return post_to_slack(
                        text=text,
                        thread_ts=new_thread_ts
                    )
                return slack_response
            else:
                logger.error(f"Slack API returned an error: {slack_response}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to post to Slack: {e}")
            return None

    # If thread_ts is provided, post the text in the existing thread
    if thread_ts:
        payload = {
            "text": text,  # Post the text as a reply in the thread
            "thread_ts": thread_ts,
            "channel": SLACK_CHANNEL
        }
        try:
            response = requests.post(
                url="https://slack.com/api/chat.postMessage",
                json=payload,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to post to Slack: {e}")
            return None


def send_sns_message(phone_number, message):
    """
    Send a text message using AWS SNS.
    """
    try:
        response = sns_client.publish(
            PhoneNumber=phone_number,
            Message=message,
            MessageAttributes={
                'AWS.SNS.SMS.SMSType': {
                    'DataType': 'String',
                    'StringValue': 'Promotional'  # Could be 'Promotional' as well
                }
            }
        )
        logger.info(f"Sent SNS message to {phone_number}. Response: {response}")
    except Exception as e:
        logger.error(f"Failed to send SNS message: {e}")


shutdown_event = threading.Event()


def escalate_to_next_tier(incident):
    """
    Escalate incident to the DevOps Manager.
    """
    ts = incident['slack_message_thread_ts']
    text = f"🚨 @channel\n Escalation: Incident {incident['incident_id']} needs your attention.\n"
    escalation_details = incident.get('escalation_details')
    if escalation_details == 'Initial escalation record created.':
        escalation_details = 'The Devops On Call did not acknowledge a new incident within the agreed escalation time'
    # text += f"Status: {incident['incident_status']}\nDetails: {escalation_details}\n"
    current_escalation_status = incident['escalation_status']
    next_escalation_point_number = DEVOPS_MANAGER_PHONE
    msg = f"escalating to DEVOPS_MANAGER: <@{get_user_id_by_nickname(DEVOPS_MANAGER_NICKNAME)['user_id']}>"
    if current_escalation_status == 'devops_escalation':
        next_escalation_point_number = DIRECTOR_PHONE
        msg = f"escalating to DIRECTOR: <@{get_user_id_by_nickname(DIRECTOR_NICKNAME)['user_id']}>"
    text = msg

    slack_response = post_to_slack(text, incident_id=incident['incident_id'], thread_ts=incident['slack_message_thread_ts'])
    if slack_response.get('warning'):
        if slack_response.get('warning') != '':
            logger.error(f"post_to_slack {slack_response.get('warning')}")
    send_sns_message(next_escalation_point_number, f"{text}")  # Replace with actual number


def get_record_by_id(incident_id, table_name):
    """
    Retrieve a record from the GitHub DynamoDB table by incident_id.

    Args:
        incident_id (str): The ID of the incident to retrieve.
        table_name
    Returns:
        dict: The retrieved record, or None if not found.
    """
    if table_name not in ["TestCyberArkIncidents", "TestGithubIncidents", "CyberArkIncidents", "GithubIncidents"]:
        raise Exception(f"Invalid table name: {table_name}")

    table = github_table

    try:
        response = table.get_item(Key={"incident_id": incident_id})
        if "Item" in response:
            logger.info(f"Record found: {response['Item']}")
            return response["Item"]
        else:
            logger.warning(f"No record found for incident_id: {incident_id}")
            return None
    except Exception as e:
        logger.error(f"Error retrieving record for incident_id {incident_id}: {e}")
        return None


def get_channel_id(channel_name):
    """
    Get the channel ID for a given channel name.
    """
    headers = {
        "Authorization": f"Bearer {SLACK_API_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(
            url="https://slack.com/api/conversations.list",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        slack_response = response.json()

        if not slack_response.get("ok"):
            logger.error(f"Slack API Error: {slack_response.get('error')}")
            return None

        # Search for the channel with the matching name
        for channel in slack_response.get("channels", []):
            if channel["name"] == channel_name:
                return channel["id"]

        logger.error(f"Channel {channel_name} not found.")
        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to retrieve channel ID: {e}")
        return None


def check_reaction_on_slack(thread_ts):
    """
    Check if there is a reaction on a Slack message identified by thread_ts.

    Args:
        thread_ts (str): The thread timestamp of the Slack message to check.

    Returns:
        bool: True if a reaction exists, False otherwise.
    """
    if not SLACK_API_TOKEN:
        logger.error("Slack API Token is not configured.")
        return False

    headers = {
        "Authorization": f"Bearer {SLACK_API_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(
            url="https://slack.com/api/reactions.get",
            params={
                "channel": get_channel_id(SLACK_CHANNEL),
                "timestamp": thread_ts
            },
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        slack_response = response.json()

        if slack_response.get("ok") and slack_response.get("message", {}).get("reactions"):
            if len(slack_response.get("message", {}).get("reactions")) > 0:
                logger.info(f"Reaction found for thread_ts {thread_ts}")
                return True
            else:
                logger.info(f"No reaction found for thread_ts {thread_ts}")
                return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to check reactions on Slack: {e}")
        return False


def get_user_id_by_nickname(nickname):
    """
    Get the Slack user ID for a given user nickname (display name).
    """
    headers = {
        "Authorization": f"Bearer {SLACK_API_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(
            url="https://slack.com/api/users.list",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        slack_response = response.json()

        if not slack_response.get("ok"):
            logger.error(f"Slack API Error: {slack_response.get('error')}")
            return {"result": "api_error", "user_id": "channel"}

        for user in slack_response.get("members", []):
            if user.get("profile", {}).get("display_name") == nickname:
                return {"nickname": nickname, "result": "failed", "user_id": user["id"]}

        logger.error(f"User with nickname {nickname} not found.")
        return {"nickname": nickname, "result": "no_user", "user_id": "channel"}

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to retrieve user ID: {e}")
        return {"nickname": nickname, "result": "failed", "user_id": "channel"}


def get_latest_incident_update(github_incident_id):
    # url = "https://www.githubstatus.com/api/v2/incidents/ltyqfp67463z.json"
    url = f"https://www.githubstatus.com/api/v2/incidents/{github_incident_id}.json"

    try:
        response = requests.get(url)
        response.raise_for_status()  # Check for any request errors
        incident_data = response.json()

        # Get the incident updates list and return the latest update
        incident_updates = incident_data['incident']['incident_updates']
        if incident_updates:
            latest_update = incident_updates[0] # The first item is the latest update
            return latest_update
        else:
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"failed get_latest_incident_update: {e}")
        return None


def handle_incident(incident):
    """
    Process and escalate incidents based on the status and timing.
    """
    incident_id = incident["incident_id"]
    thread_ts = incident.get("slack_message_thread_ts")
    updated_at = datetime.fromisoformat(incident["last_incident_update_time"])
    escalation_status = incident.get("escalation_status")
    incident_status = incident.get("incident_status")
    current_time = datetime.now(timezone.utc)
    current_time_to_acknowledge = (current_time - updated_at).seconds
    github_incident = get_record_by_id(incident_id, GITHUB_TABLE_NAME)
    github_incident_id = github_incident["incident_id"]
    last_update = get_latest_incident_update(github_incident_id)

    if last_update:
        update_id = last_update["id"]
        update_message = last_update["body"]
        update_status = last_update["status"]
        if update_id != github_incident['last_update_id']:
            update_table_attribute(incident_id=incident['incident_id'], attribute_name="last_update_id", attribute_value=update_id, update_table_name=GITHUB_TABLE_NAME)
            if thread_ts:
                post_to_slack(text=f"new gitlab update:\n{update_message}", thread_ts=thread_ts)
            if update_status != github_incident['github_status'].lower():
                update_table_attribute(incident_id=incident['incident_id'], attribute_name="github_status", attribute_value=update_status, update_table_name=GITHUB_TABLE_NAME)
                if update_status in ["resolved", "postmortem"]:
                    update_table_attribute(incident_id=incident['incident_id'], attribute_name="incident_status", attribute_value="update_status", update_table_name=CYBERARK_TABLE_NAME)

    if incident['incident_status'] == "new":
        result = get_user_id_by_nickname(DEVOPS_ON_CALL)
        # component without existing incident on GitHub
        if 'cyberark' in github_incident_id:
            subject = f'Incident ID: {incident["incident_id"]}, Component {github_incident["name"]} in Github is currently in status {github_incident["status"]} with no active Github Incident. Impact: {github_incident["impact"]}'
        else:
            subject = f'New Github Incident, ID: {incident["incident_id"]}  Name: {github_incident["name"]} was detected. Impact: {github_incident["impact"]}'
        text = f"Incident {incident['incident_id']} needs attention. <@{result['user_id']}>"
        slack_response = post_to_slack(text=text, subject=subject, incident_id=incident['incident_id'])
        update_table_attribute(incident_id=incident['incident_id'], attribute_name="incident_status", attribute_value="published_to_slack", update_table_name=CYBERARK_TABLE_NAME)
        update_table_attribute(incident_id=incident['incident_id'], attribute_name="last_incident_update_time", attribute_value=current_time.isoformat(), update_table_name=CYBERARK_TABLE_NAME)

        incident["incident_status"] = "published_to_slack"
        incident["slack_message_thread_ts"] = slack_response['ts']
        thread_ts = slack_response['ts']

    if thread_ts:
        if last_update:
            if update_id != github_incident['last_update_id']:
                post_to_slack(text=f"new gitlab update:\n{update_message}", thread_ts=thread_ts)
        if check_reaction_on_slack(thread_ts):
            update_table_attribute(incident_id, "acknowledged", "incident_status", update_table_name=CYBERARK_TABLE_NAME)
            update_table_attribute(incident_id, datetime.now(timezone.utc).isoformat(), "acknowledgment_time", update_table_name=CYBERARK_TABLE_NAME)
            update_table_attribute(incident_id, datetime.now(timezone.utc).isoformat(), "last_incident_update_time", update_table_name=CYBERARK_TABLE_NAME)
            return

    acknowledge_time_exceeded = current_time_to_acknowledge > TIME_TO_ACKNOWLEDGE
    time_to_next_escalation_exceeded = (current_time - updated_at).seconds > TIME_TO_CANCEL_NEXT_ESCALATION
    # if TEST_FLOW == "true":
    #     time_to_next_escalation_exceeded = True
    #     acknowledge_time_exceeded = True
    if incident_status in ['new', 'published_to_slack'] and escalation_status == "Pending" and acknowledge_time_exceeded:
        # Escalate to DevOps Manager
        update_table_attribute(incident_id=incident['incident_id'], attribute_name="escalation_status", attribute_value="devops_escalation", update_table_name=CYBERARK_TABLE_NAME)
        update_table_attribute(incident_id=incident['incident_id'], attribute_name="last_escalation_update_time", attribute_value=current_time.isoformat(), update_table_name=CYBERARK_TABLE_NAME)
        ts = incident['slack_message_thread_ts']
        escalate_to_next_tier(incident)
        incident["escalation_status"] = "devops_escalation"

    if incident["escalation_status"] == "devops_escalation" and time_to_next_escalation_exceeded:
        # Escalate to R&D Director
        update_table_attribute(incident_id=incident['incident_id'], attribute_name="escalation_status", attribute_value="director_escalation", update_table_name=CYBERARK_TABLE_NAME)
        update_table_attribute(incident_id=incident['incident_id'],attribute_name="last_escalation_update_time", attribute_value=current_time.isoformat(), update_table_name=CYBERARK_TABLE_NAME)
        ts = incident['slack_message_thread_ts']
        escalate_to_next_tier(incident)
        incident["escalation_status"] = "director_escalation"


def notifier_service():
    """
    Main notifier service logic:
    - Fetch incidents with pending escalation stages.
    - Handle escalations and notify the appropriate people.
    """
    logger.info("Starting Notifier Service...")
    while not shutdown_event.is_set():
        try:
            incidents = get_incidents()
            for incident in incidents:
                handle_incident(incident)
            time.sleep(CHECK_INTERVAL)  # Wait before the next check
        except Exception as e:
            logger.error(f"Unexpected error in notifier service: {e}")


if __name__ == "__main__":
    secrets = get_secrets()
    SLACK_API_TOKEN = secrets.get("slack_app_bot_token")
    DIRECTOR_PHONE = secrets.get("director_phone")
    DIRECTOR_NICKNAME = secrets.get("director_nickname")
    DEVOPS_MANAGER_PHONE = secrets.get("devops_manager_phone")
    DEVOPS_MANAGER_NICKNAME = secrets.get("devops_manager_nickname")
    SLACK_CHANNEL = TEST_CHANNEL if TEST_FLOW else PROD_CHANNEL

    notifier_service()
