import os
import threading
import time
import boto3
import json
import requests
import uuid
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# Configuration Constants
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 300))  # Default to 300 seconds
MAX_RETRIES = 3  # Maximum retries for failed API calls
TEST_FLOW = os.getenv("TEST_FLOW", "false").lower() == "true"  # Enable test flow

# Table Names based on TEST_FLOW
GITHUB_TABLE_NAME = os.getenv("GITHUB_TABLE_NAME", "TestGithubIncidents" if TEST_FLOW else "GithubIncidents")
CYBERARK_TABLE_NAME = os.getenv("CYBERARK_TABLE_NAME", "TestCyberArkIncidents" if TEST_FLOW else "CyberArkIncidents")

# DynamoDB Setup
dynamodb = boto3.resource("dynamodb", region_name="us-west-2")
github_table = dynamodb.Table(GITHUB_TABLE_NAME)
cyberark_table = dynamodb.Table(CYBERARK_TABLE_NAME)

# GitHub Status API URL
SUMMARY_URL = "https://www.githubstatus.com/api/v2/summary.json"

# Logging Configuration
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s")
logger = logging.getLogger(__name__)

# FastAPI Application Setup
app = FastAPI()


class HealthResponse(BaseModel):
    status: str


@app.get('/health', response_model=HealthResponse)
def health():
    """
    Liveness probe to indicate the application is running.
    """
    return HealthResponse(status="healthy")


@app.get('/readiness', response_model=HealthResponse)
def readiness():
    """
    Readiness probe to check if the application is ready to serve traffic.
    """
    try:
        # Check DynamoDB table existence
        tables = dynamodb.meta.client.list_tables()
        if GITHUB_TABLE_NAME not in tables.get("TableNames", []):
            raise HTTPException(status_code=503, detail=f"DynamoDB table '{GITHUB_TABLE_NAME}' not found")
        if CYBERARK_TABLE_NAME not in tables.get("TableNames", []):
            raise HTTPException(status_code=503, detail=f"DynamoDB table '{CYBERARK_TABLE_NAME}' not found")

        # Check GitHub Status API accessibility
        try:
            fetch_github_summary()
        except RuntimeError as api_error:
            raise HTTPException(status_code=503, detail=f"GitHub API check failed: {api_error}")

        # All checks passed
        return HealthResponse(status="ready")

    except Exception as e:
        logger.error(f"Readiness probe failed: {e}")
        raise HTTPException(status_code=503, detail=f"Unexpected error: {str(e)}")


def fetch_github_summary():
    """
    Fetch the GitHub Status API summary data.
    """
    try:
        session = requests.Session()
        session.headers.update({"Accept": "application/json"})
        response = session.get(SUMMARY_URL, timeout=10, verify=True)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as request_error:
        raise RuntimeError(f"GitHub API request failed: {request_error}")
    except ValueError:
        raise RuntimeError("Invalid JSON received from GitHub API")
    except Exception as general_error:
        raise RuntimeError(f"Unexpected error during GitHub API fetch: {general_error}")


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


def process_github_summary(data):
    """
    Parse the GitHub summary data and identify incidents and faulty components.
    """
    incidents = []
    try:
        if not isinstance(data.get("incidents", []), list) or not isinstance(data.get("components", []), list):
            raise ValueError("Unexpected structure in GitHub API response")

        # Process GitHub Incidents
        for incident in data["incidents"]:
            affected_components = [
                component["name"]
                for component in data["components"]
                if component.get("group_id") == incident["id"] and component["status"] != "operational"
            ]

            incidents.append({
                "incident_id": incident["id"],
                "internal_incident_id": f"cyberark-{uuid.uuid4()}",
                "created_at": incident["created_at"],
                "impact": incident["impact"],
                "status": incident["status"],
                "name": incident["name"],
                "updated_at": incident["updated_at"],
                "resolved_at": incident.get("resolved_at", ""),
                "affected_components": affected_components,
                "last_update_id": incident.get("last_update_id", ""),
                "github_status": incident["status"]
            })

        # Process Faulty Components without Incidents
        for component in data["components"]:
            if component["status"] != "operational" and not component.get("group_id"):
                internal_id = f"cyberark-{uuid.uuid4()}"
                incidents.append({
                    "incident_id": internal_id,
                    "internal_incident_id": internal_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "impact": "unknown",
                    "status": component.get("status", "unknown"),
                    "name": component.get("name", "unknown_component"),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "resolved_at": "",
                    "last_update_id": 0,
                    "affected_components": [component.get("name", "unknown_component")],
                    "github_status": component.get("status", "unknown")
                })
    except Exception as e:
        logger.error(e)
    return incidents


def log_to_tables(incidents):
    """
    Log incidents and related escalation data into DynamoDB tables.
    """
    for incident in incidents:
        existing_record = get_record_by_id(incident['incident_id'], GITHUB_TABLE_NAME)
        try:
            if not existing_record:
                # Log incident in GitHub table
                github_table.put_item(Item={
                    "incident_id": incident["incident_id"],
                    "internal_incident_id": incident["internal_incident_id"],
                    "created_at": incident["created_at"],
                    "impact": incident["impact"],
                    "status": incident["status"],
                    "name": incident["name"],
                    "updated_at": incident["updated_at"],
                    "resolved_at": incident.get("resolved_at", ""),
                    "last_update_id": incident.get("last_update_id", ""),
                    "affected_components": json.dumps(incident["affected_components"]),
                    "github_status": incident["status"]
                })
                now_time = datetime.now(timezone.utc).isoformat()
                # Log corresponding escalation record in CyberArk table
                cyberark_table.put_item(Item={
                    "incident_id": incident["incident_id"],
                    "internal_incident_id": incident["internal_incident_id"],
                    "escalation_status": "Pending",
                    "incident_status": "new",
                    "last_escalation_update_time": now_time,
                    "last_incident_update_time": now_time,
                    "escalation_details": "Initial escalation record created.",
                    "created_at": now_time,
                    "acknowledgment_time": "",
                    "slack_message_thread_ts": None
                })

        except Exception as log_error:
            logger.error(f"Failed to log incident '{incident['incident_id']}': {log_error}")


shutdown_event = threading.Event()


def monitor_github_service(max_cycles=None, override_wait_time=False):
    """
    Continuously monitor the GitHub Status API and handle retries for failures.
    If max_cycles is provided, the loop will terminate after the given number of cycles.
    """
    consecutive_failures = 0
    cycles = 0

    while not shutdown_event.is_set():
        try:
            logger.debug("Fetching GitHub summary.")
            summary_data = fetch_github_summary()
            logger.debug(f"Summary fetched: {summary_data}")

            incidents = process_github_summary(summary_data)
            logger.debug(f"Incidents processed: {incidents}")

            if incidents:
                log_to_tables(incidents)
                logger.info(f"Logged {len(incidents)} incident(s) to DynamoDB.")
            else:
                logger.info("No issues detected. All systems operational.")

            consecutive_failures = 0
        except RuntimeError as api_error:
            consecutive_failures += 1
            logger.warning(f"API call failed ({consecutive_failures}/{MAX_RETRIES}): {api_error}")

            if consecutive_failures >= MAX_RETRIES:
                internal_id = f"monitoring_failure-{uuid.uuid4()}"
                log_to_tables([{
                    "incident_id": internal_id,
                    "internal_incident_id": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "impact": "monitoring_failure",
                    "status": "Monitoring Failure",
                    "name": "Monitoring system unable to fetch GitHub status",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "affected_components": [],
                    "last_update_id": "",
                    "github_status": "Monitoring Failure"
                }])
                logger.error(f"Monitoring failure logged with incident ID: {internal_id}")
                consecutive_failures = 0
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

        if max_cycles:
            cycles += 1
            if cycles >= max_cycles:
                break

        if override_wait_time is False:
            time.sleep(CHECK_INTERVAL)


if __name__ == '__main__':
    logger.info(f"Starting monitor service with TEST_FLOW={TEST_FLOW}, CHECK_INTERVAL={CHECK_INTERVAL} seconds.")

    # Start the monitor service in a separate thread
    monitor_thread = threading.Thread(target=monitor_github_service)
    monitor_thread.start()

    # Run the FastAPI server
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=True, log_level="error")
