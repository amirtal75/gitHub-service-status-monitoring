# Code explanation:
    service can run in test mode by setting env var TEST_FLOW = true in the services config map

    monitor service is responsible for tracking the Githun Status API for Incidents or fault components.
    it saves data related to github in a DynamoDB table in a table GITHUB_TABLE_NAME = os.getenv("GITHUB_TABLE_NAME", "TestGithubIncidents" if TEST_FLOW else "GithubIncidents")
    it saves data related to cyberark internal incident flow in a DynamoDB table in a table CYBERARK_TABLE_NAME = os.getenv("CYBERARK_TABLE_NAME", "TestCyberArkIncidents" if TEST_FLOW else "CyberArkIncidents")
    
    notifier service is responsible for several roles:
        1. Track the internal table for incidents in status new and notify in slack mentioning @devops_on_call and if not defined then @channel
        2. Trach githun status for existing incidents and list the last update data to slack and change status in tables accordingly
        3. listen to slack threads for unreslved incidents and decide on escalation with configurable time in values.yaml:
              TIME_TO_ACKNOWLEDGE: 900 # 15 minutes
              TIME_TO_CANCEL_NEXT_ESCALATION: 7200 # 2 hours
            a. if not acknowledged by TIME_TO_ACKNOWLEDGE seconds then escalate to devops_manager (details on implementation below) and update incident["escalation_status"] == "devops_escalation"
            b. if not acknowledged by TIME_TO_CANCEL_NEXT_ESCALATION seconds and incident["escalation_status"] == "devops_escalation" then escalate to director (details on implementation below)  and update incident["escalation_status"] == "director_escalation"
            c. if acknowledged then escalation will not continue
            d. update when incident is resolved by github or post mortem
        4. Escalation are notified in slack mentioning the user nickname of the devops-Manager and director to ping them.
           Additionally sens and SMS to thier phone number using AWS SNS Service (More detials below)

# Steps to deploy:

# create slack app
    you need to create a slack app and install it your workspace.
    In section OAuth & Permissions of teh app management give it permissions: chat:write, im:read, im:write, reactions:read, channels:read
    extract the Oauth bot token
# how to deploy the solution:
    # 0. install packages for python3, git, terraform
    # 1. clone the repo https://github.com/amirtal75/your_code_repo.git
    # 2. configure your local env in aws cli with aws credentials in sufficient permissions
    # 3. make sure that aws credentials are for a dev account
    # 4. cd env_setup_and_clean and run create_terraform_backend_with_arn.py 
    # 5. cd ../ && terraform init
    # 6. terraform plan to check the resources to be created (EKS, VPC, IAM, etc)
    # 7. terraform apply
    # 8. terraform output > env_setup_and_clean\output_tf.txt
    # 9. cat env_setup_and_clean\output_tf.txt | grep sg-
    # 10. create a docker image for monitor service and notifier service and uplaod them to your docker hub tag them as v1.0.0
    # 11.   in aws secret manager using cli update:
            slack_app_bot_token - aws secretsmanager update-secret --secret-id slack_app_bot_token --secret-string '{\"slack_app_bot_token\":\"Oauth bot token from step 1\"}'
            director_phone - aws secretsmanager update-secret --secret-id director_phone --secret-string '{\"Phone\":\"+972your_phone\"}'
            devops_manager_phone - aws secretsmanager update-secret --secret-id devops_manager_phone --secret-string '{\"Phone\":\"+972your_phone\"}'
            director_nickname - aws secretsmanager update-secret --secret-id director_nickname --secret-string '{\"director_nickname\":\"your_slack_nickname\"}'
            devops_manager_nickname - aws secretsmanager update-secret --secret-id devops_manager_nickname --secret-string '{\"devops_manager_nickname\":\"your_slack_nickname\"}'

# NO scaling support
    though there is helm support for hpa, the code itself is not ready yet to handle situations where multiple pods of the same service are running.
    this need lock mechanisms to ensure different pods wont update the same item


# text messaging
    for sms messaging to work you need to either opt out of sandbox in aws, or add verified phone numbers for the escalation contacts you define
    the monthly limit of SMS is 1$ which will limit the amount of messages you can send.
    You need to ask AWS support to increase the quota or ot out of sandbox and choose a payment plan

# Github Repo Config
    the following secrets need to be defined in the github repo
    AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY
    DOCKER_USERNAME
    PAT

# Workflow RUN
    currently the workflow need to be run manually
    you can uncomment the on push section in the workflow to automatic deploy on commit to main
    currently the workflow on push to main branch, does all stages besides rollback and is not production ready (automatic terraform apply and deploy)
    push to a side branch to avoid deployment

# Things Left to Implement
    1. setup grafna and promethues on the cluster and create a prometheus exporter to scrape metrics endpoint on port 8000
    2. add a Gauge in monitor service to count the number of incidents
    3. add a Gauge in notifier service to list the time between incident creation and acknowledge
    4. add a Gauge in notifier service to list the time between incident creation and resolution
    5. add a Gauge in notifier service to list the time between incident creation and escalation to tier1
    6. add a Gauge in notifier service to list the time between incident creation and escalation to tier2
    7. Create Dashboards for the above metrics and possible create further alerting mechnism using grafan alerts
    7. add a Gauge for counting API failure to slack using limit exceeded and alert if thats the case
    7. add a Gauge for counting API failure to Github Status and alert to on-call if thats the case to validate teh company status
    7. add a Gauge for counting action failures to DynamoDB using and alert if thats the case (easy to implement currently within code but can be noisy without optimization)

# Consideration for HA
    1. Standard HA is defined by HPA with max replicas by cpu consumption.
    2. further HA can be implmented regionally in different az, and the master pod will be defined to be somewhere specific and will update a keep alive time
       the slave pods will identify if too long a duration has passed since the keep alive signal, and will stop once the keep alive signal returns
    3. Same solution as 2, but in a diffent region and in a different cloud provider, in case the an entire AWS region shuts down, there may be a case where we 
       have no indication if the services are working or not. we can have slave pods in the oher cloud provider also listen for a keep alive signal (allow peering between clusters).
       if noe live signal then attempt to replictae the databases with the last 24 hours data from AWS to GCP, 
       upon possibel failure have a DR function that will go over all github incidents that are not resolved or post mortem and update thier data in the database. all incidents that are 
       in identifed or new state will be treated as new incidents, all otehrs will recive automatiov escalation to tier1 in addition to on call and continure fomr there
    4, this is besides the assignment but its


  
