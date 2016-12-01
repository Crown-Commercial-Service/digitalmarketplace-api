from apps.jira import JIRAAPI
import os

creds = os.environ['JIRA_CREDS']

j = JIRAAPI()
