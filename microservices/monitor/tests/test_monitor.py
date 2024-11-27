import json
import logging
import unittest
from unittest.mock import patch, MagicMock
import os
import boto3
import requests
import uuid
from botocore.exceptions import ClientError
from microservices.monitor.app import fetch_github_summary, process_github_summary, log_to_tables, monitor_github_service


def generate_uuid():
    return str(uuid.uuid4())


class TestSpecialScenarios(unittest.TestCase):

    def setUp(self):
        os.environ["TEST_FLOW"] = "true"  # Enable test flow for using test DynamoDB tables
        self.dynamodb = boto3.resource("dynamodb", region_name="us-west-2")
        self.github_table_name = "TestGithubIncidents"
        self.cyberark_table_name = "TestCyberArkIncidents"

        # Ensure the tables exist
        self.github_table = self.dynamodb.Table(self.github_table_name)
        self.cyberark_table = self.dynamodb.Table(self.cyberark_table_name)
        self.assert_table_exists(self.github_table_name)
        self.assert_table_exists(self.cyberark_table_name)

    def assert_table_exists(self, table_name):
        try:
            table = self.dynamodb.Table(table_name)
            table.load()  # Load metadata to check existence
        except Exception as e:
            self.fail(f"DynamoDB table '{table_name}' does not exist or cannot be loaded: {e}")


    @patch("microservices.monitor.app.requests.Session.get")
    def test_multiple_simultaneous_incidents_with_uuid(self, mock_get):
        mock_data = {
            "status": {"description": "Partial Outage"},
            "components": [
                {"id": "comp-1", "name": "API Requests", "status": "major_outage", "group_id": str(uuid.uuid4())},
                {"id": "comp-2", "name": "Webhooks", "status": "partial_outage", "group_id": str(uuid.uuid4())},
                {"id": "comp-3", "name": "Actions", "status": "degraded_performance", "group_id": str(uuid.uuid4())},
                {"id": "comp-4", "name": "Pages", "status": "partial_outage", "group_id": str(uuid.uuid4())},
                {"id": "comp-5", "name": "Codespaces", "status": "major_outage", "group_id": str(uuid.uuid4())}
            ],
            "incidents": [
                {
                    "id": str(uuid.uuid4()),
                    "name": "API Outage",
                    "status": "investigating",
                    "impact": "critical",
                    "created_at": "2024-11-23T12:00:00Z",
                    "updated_at": "2024-11-23T12:30:00Z"
                },
                {
                    "id": str(uuid.uuid4()),
                    "name": "API Outage",
                    "status": "investigating",
                    "impact": "critical",
                    "created_at": "2024-11-23T12:00:00Z",
                    "updated_at": "2024-11-23T12:30:00Z"
                },
                {
                    "id": str(uuid.uuid4()),
                    "name": "API Outage",
                    "status": "investigating",
                    "impact": "critical",
                    "created_at": "2024-11-23T12:00:00Z",
                    "updated_at": "2024-11-23T12:30:00Z"
                },
                {
                    "id": str(uuid.uuid4()),
                    "name": "Webhooks Latency",
                    "status": "monitoring",
                    "impact": "high",
                    "created_at": "2024-11-23T13:00:00Z",
                    "updated_at": "2024-11-23T13:15:00Z"
                },
                {
                    "id": str(uuid.uuid4()),
                    "name": "Actions Delay",
                    "status": "investigating",
                    "impact": "medium",
                    "created_at": "2024-11-23T14:00:00Z",
                    "updated_at": "2024-11-23T14:30:00Z"
                },
                {
                    "id": str(uuid.uuid4()),
                    "name": "Pages Outage",
                    "status": "monitoring",
                    "impact": "low",
                    "created_at": "2024-11-23T15:00:00Z",
                    "updated_at": "2024-11-23T15:15:00Z"
                },
                {
                    "id": str(uuid.uuid4()),
                    "name": "Codespaces Crash",
                    "status": "investigating",
                    "impact": "critical",
                    "created_at": "2024-11-23T16:00:00Z",
                    "updated_at": "2024-11-23T16:30:00Z"
                }
            ]
        }
        mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_data)

        incidents = process_github_summary(mock_data)
        log_to_tables(incidents)
        self.assertEqual(len(incidents), 7, "Number of processed incidents does not match input.")
        for incident in incidents:
            self.assertTrue(uuid.UUID(incident["incident_id"]))

    def test_non_operational_component_logs_to_dynamo_and_escalation_table(self):
        # Mock data with a non-operational component
        mock_data = {
            "components": [
                {"id": "comp-1", "name": "API Requests", "status": "partial_outage", "group_id": None}
            ],
            "incidents": []  # No incidents provided
        }

        # Process the mock data into incidents
        incidents = process_github_summary(mock_data)

        # Assertions: Verify one incident was created
        self.assertEqual(len(incidents), 1, "Expected one incident created for the non-operational component.")

        # Log the incidents to DynamoDB
        log_to_tables(incidents)

        # Fetch the logged incident from the GitHub table
        created_incident = incidents[0]
        github_response = self.github_table.get_item(Key={"incident_id": created_incident["incident_id"]})
        self.assertIn("Item", github_response, "Incident was not logged in the GitHub table.")
        github_item = github_response["Item"]

        # Validate the logged GitHub data
        self.assertEqual(github_item["incident_id"], created_incident["incident_id"], "Logged GitHub incident ID mismatch.")
        self.assertEqual(github_item["name"], "API Requests", "Logged GitHub incident name mismatch.")
        self.assertEqual(github_item["github_status"], "partial_outage", "Logged GitHub incident status mismatch.")
        self.assertEqual(github_item["impact"], "unknown", "Logged GitHub incident impact mismatch.")
        self.assertEqual(github_item["resolved_at"], "", "Logged GitHub incident resolved_at mismatch.")
        self.assertIn("API Requests", json.loads(github_item["affected_components"]), "Logged GitHub affected components mismatch.")

        # Fetch the logged escalation from the CyberArk table
        cyberark_response = self.cyberark_table.get_item(Key={"incident_id": created_incident["incident_id"]})
        self.assertIn("Item", cyberark_response, "Incident was not logged in the CyberArk escalation table.")
        cyberark_item = cyberark_response["Item"]

        # Validate the logged CyberArk escalation data
        self.assertEqual(cyberark_item["incident_id"], created_incident["incident_id"], "Logged CyberArk incident ID mismatch.")
        self.assertEqual(cyberark_item["escalation_status"], "Pending", "Escalation status mismatch.")
        self.assertIn("Initial escalation record created.", cyberark_item["escalation_details"], "Escalation details mismatch.")

        print(f"GitHub Incident logged successfully: {github_item}")
        print(f"CyberArk Escalation logged successfully: {cyberark_item}")

    def test_incident_status_changes(self):
        incident_id = str(uuid.uuid4())
        mock_data_initial = {
            "incidents": [
                {
                    "id": incident_id,
                    "status": "investigating",
                    "name": "API Issue",
                    "impact": "high",
                    "created_at": "2024-11-23T12:00:00Z",
                    "updated_at": "2024-11-23T12:30:00Z",
                    "affected_components": ["API Requests"],
                }
            ],
            "components": [
                {"id": "comp-1", "name": "API Requests", "status": "partial_outage", "group_id": incident_id}
            ],
        }
        mock_data_resolved = {
            "incidents": [
                {
                    "id": incident_id,
                    "status": "resolved",
                    "name": "API Issue",
                    "impact": "high",
                    "created_at": "2024-11-23T12:00:00Z",
                    "updated_at": "2024-11-23T13:00:00Z",
                    "resolved_at": "2024-11-23T13:00:00Z",
                    "affected_components": ["API Requests"],
                }
            ],
            "components": [
                {"id": "comp-1", "name": "API Requests", "status": "operational", "group_id": incident_id}
            ],
        }

        # Initial processing
        incidents_initial = process_github_summary(mock_data_initial)
        self.assertEqual(len(incidents_initial), 1)
        self.assertEqual(incidents_initial[0]["incident_id"], incident_id)
        self.assertEqual(incidents_initial[0]["status"], "investigating")
        self.assertEqual(incidents_initial[0]["resolved_at"], "", "resolved_at should default to an empty string.")

        # Resolved processing
        incidents_resolved = process_github_summary(mock_data_resolved)
        self.assertEqual(len(incidents_resolved), 1)
        self.assertEqual(incidents_resolved[0]["incident_id"], incident_id)
        self.assertEqual(incidents_resolved[0]["status"], "resolved")
        self.assertEqual(incidents_resolved[0]["resolved_at"], "2024-11-23T13:00:00Z", "Resolved time mismatch.")

    def test_scheduled_maintenance_handling(self):
        mock_data = {
            "scheduled_maintenances": [
                {"id": "maintenance-1", "name": "Database Upgrade", "status": "in_progress"}
            ],
            "components": [],
            "incidents": []
        }
        incidents = process_github_summary(mock_data)
        self.assertEqual(len(incidents), 0)

    # @patch("microservices.monitor.app.requests.Session.get")
    # @patch("microservices.monitor.app.process_github_summary")
    def test_historical_data_handling(self):
        mock_data = {
            "incidents": [
                {
                    "id": str(uuid.uuid4()),
                    "name": "Stale Incident",
                    "status": "resolved",
                    "impact": "low",  # Impact field is expected
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T12:00:00Z",
                    "incident_updates": [  # Optional field for updates
                        {
                            "updated_at": "2024-01-01T12:00:00Z",
                            "status": "resolved",
                            "body": "Incident resolved successfully."
                        }
                    ]
                }
            ],
            "components": []  # Components are optional here
        }

        incidents = process_github_summary(mock_data)

        # Validate the processed incidents
        self.assertEqual(len(incidents), 1, "Expected exactly one processed incident.")
        self.assertEqual(incidents[0]["status"], "resolved", "Incident status should be 'resolved'.")
        self.assertEqual(incidents[0]["name"], "Stale Incident", "Incident name mismatch.")

    def test_unknown_component_status(self):
        mock_data = {
            "components": [{"id": "1", "name": "API", "status": "unexpected_status"}],
            "incidents": []
        }
        incidents = process_github_summary(mock_data)
        self.assertEqual(len(incidents), 1)
        self.assertEqual(incidents[0]["status"], "unexpected_status")

    def test_regional_incident_reporting(self):
        mock_data = {
            "incidents": [
                {"id": str(uuid.uuid4()), "name": "Regional Outage", "status": "investigating", "impact": "high", "regions": ["eu-west-1"], "created_at": "2024-11-23T12:00:00Z", "updated_at": "2024-11-23T12:30:00Z"}
            ],
            "components": []
        }
        incidents = process_github_summary(mock_data)
        self.assertEqual(len(incidents), 1)
        self.assertEqual(incidents[0]["name"], "Regional Outage")

    @patch("microservices.monitor.app.requests.Session.get")
    def test_api_timeout_handling(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout()
        with self.assertRaises(RuntimeError):
            fetch_github_summary()


class TestMonitorService(unittest.TestCase):

    def setUp(self):
        os.environ["TEST_FLOW"] = "true"
        self.dynamodb = boto3.resource("dynamodb", region_name="us-west-2")
        self.github_table_name = "TestGithubIncidents"
        self.cyberark_table_name = "TestCyberArkIncidents"
        self.assert_table_exists(self.github_table_name)
        self.assert_table_exists(self.cyberark_table_name)

    def assert_table_exists(self, table_name):
        """Verify that a DynamoDB table exists."""
        try:
            table = self.dynamodb.Table(table_name)
            table.load()
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                self.fail(f"DynamoDB table '{table_name}' does not exist.")
            else:
                raise

    @patch("microservices.monitor.app.requests.Session.get")
    def test_fetch_github_summary_timeout(self, mock_get):
        """Test handling of API timeout."""
        mock_get.side_effect = requests.exceptions.Timeout("Timeout occurred")
        with self.assertRaises(RuntimeError, msg="Timeout exception not handled correctly."):
            fetch_github_summary()

    @patch("microservices.monitor.app.requests.Session.get")
    def test_fetch_github_summary_invalid_json(self, mock_get):
        """Test handling of invalid JSON responses."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html>Not JSON</html>"
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response
        with self.assertRaises(RuntimeError, msg="Invalid JSON exception not handled correctly."):
            fetch_github_summary()

    def test_process_github_summary_with_uuid(self):
        """Test summary processing with valid UUIDs."""
        mock_data = {
            "status": {"description": "Partial Outage"},
            "components": [
                {"id": "1", "name": "API Requests", "status": "partial_outage", "group_id": generate_uuid()}
            ],
            "incidents": [
                {
                    "id": generate_uuid(),
                    "name": "API Issue",
                    "status": "investigating",
                    "impact": "high",
                    "created_at": "2024-11-23T12:00:00Z",
                    "updated_at": "2024-11-23T12:30:00Z"
                }
            ]
        }
        result = process_github_summary(mock_data)
        logging.debug(f"Processed result: {result}")
        self.assertEqual(len(result), 1, "Incident count mismatch.")
        self.assertEqual(result[0]["name"], "API Issue", "Incident name mismatch.")

    def test_log_to_tables_uuid(self):
        """Test logging incidents to DynamoDB with UUIDs."""
        incident_id = generate_uuid()
        mock_incidents = [
            {
                "incident_id": incident_id,
                "internal_incident_id": f"cyberark-{uuid.uuid4()}",
                "created_at": "2024-11-23T12:00:00Z",
                "impact": "high",
                "status": "investigating",
                "name": "UUID Incident Test",
                "updated_at": "2024-11-23T12:30:00Z",
                "affected_components": ["API"],
                "history": [{"timestamp": "2024-11-23T12:00:00Z", "event": "Created"}],
            }
        ]
        log_to_tables(mock_incidents)

        github_table = self.dynamodb.Table(self.github_table_name)
        response = github_table.get_item(Key={"incident_id": incident_id})
        logging.debug(f"DynamoDB response: {response}")
        self.assertEqual(response["Item"]["status"], "investigating", "Incident status mismatch.")

    @patch("microservices.monitor.app.fetch_github_summary")
    @patch("microservices.monitor.app.log_to_tables")
    def test_monitor_flow_full_cycle(self, mock_log, mock_fetch):
        """Test the complete monitoring flow."""
        mock_fetch.side_effect = [
            {"status": {"description": "Operational"}, "components": [], "incidents": []},
            {"status": {"description": "Partial Outage"},
             "components": [{"id": "1", "name": "API", "status": "partial_outage"}], "incidents": []},
        ]

        monitor_github_service(max_cycles=2, override_wait_time=True)

        self.assertEqual(mock_fetch.call_count, 2, "fetch_github_summary was not called twice.")
        self.assertEqual(mock_log.call_count, 1, "log_to_tables was not called once.")

    @patch("boto3.resource")
    def test_log_to_tables_write_failure(self, mock_boto3_resource):
        mock_table = MagicMock()
        mock_table.put_item.side_effect = ClientError(
            {"Error": {"Code": "ProvisionedThroughputExceededException"}}, "PutItem"
        )
        mock_boto3_resource.return_value.Table.return_value = mock_table

        with self.assertLogs(level="ERROR") as log:
            log_to_tables([{"incident_id": generate_uuid(), "status": "investigating"}])
            self.assertIn("Failed to log incident", log.output[0])


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
    unittest.main()
