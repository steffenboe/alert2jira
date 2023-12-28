from fastapi import FastAPI, HTTPException, Body
import os
from pydantic import BaseModel
import requests
from typing import Any

app = FastAPI()


class Grafana8Notification(BaseModel):
    title: str
    message: str

@app.get('/liveness')
def liveness():
    jira_url = os.environ.get('JIRA_API_URL')
    jira_username = os.environ.get('JIRA_USERNAME')
    jira_api_token = os.environ.get('JIRA_API_TOKEN')
    #jira_project_key = os.environ.get('JIRA_PROJECT_KEY')

    if not all([jira_url, jira_username, jira_api_token]):
        raise HTTPException(status_code=500, detail='Jira environment variables are not properly set')
    
    return {'status': 'OK'}

@app.get('/readiness')
def readiness():
    jira_url = os.environ.get('JIRA_API_URL')
    jira_username = os.environ.get('JIRA_USERNAME')
    jira_api_token = os.environ.get('JIRA_API_TOKEN')
    
    if check_jira_api_health(jira_url, jira_username, jira_api_token):
        return {'status': 'OK'}
    else:
        raise HTTPException(status_code=503, detail='Jira API is not healthy')

def check_jira_api_health(jira_url, jira_username, jira_api_token):
    loglevel = os.environ.get('LOGLEVEL')
    try:
        url = f"{jira_url}/rest/api/2/myself"
        response = requests.get(
            url,
            auth=(jira_username, jira_api_token),
            timeout=5
        )

        if 200 <= response.status_code < 300:
            if loglevel == "DEBUG":
                print("Jira API is healthy")
            return True
        else:
            print(f"Jira API returned a non-success status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"Failed to connect to Jira API: {e}")
        return False
    
@app.post('/dummy')
async def dummy_webhook(payload: Any = Body(None)):
    print(payload)
    return payload

@app.post('/grafana8-webhook')
async def grafana8_webhook(notification: Grafana8Notification):
    summary = notification.dict()['title']
    description = notification.dict()['message']
    create_jira_issue(summary,description)
    return {'message': 'Webhook received successfully'}

def create_jira_issue(summary,description,jira_project_key=None):
    jira_url = os.environ.get('JIRA_API_URL')
    jira_username = os.environ.get('JIRA_USERNAME')
    jira_api_token = os.environ.get('JIRA_API_TOKEN')
    if not jira_project_key:
        jira_project_key = os.environ.get('JIRA_PROJECT_KEY')
    loglevel = os.environ.get('LOGLEVEL')

    if not (jira_url and jira_username and jira_api_token and jira_project_key):
        raise ValueError("JIRA_API_URL, JIRA_USERNAME, JIRA_API_TOKEN and JIRA_PROJECT_KEY must be set.")
    if loglevel == "DEBUG":
        print(summary, description, jira_project_key)
    issue_data = {
        'fields': {
            'project': {'key': jira_project_key},
            'summary': summary,
            'description': description,
            'issuetype': {'id': '3'},
        }
    }
    if loglevel == "DEBUG":
        print(issue_data)
    response = requests.post(
        f'{jira_url}/rest/api/2/issue/',
        json=issue_data,
        auth=(jira_username, jira_api_token),
        headers={'Content-Type': 'application/json'}
    )

    if response.status_code == 201:
        print('Jira issue created successfully')
    else:
        print(f'Failed to create Jira issue. Status code: {response.status_code}, Error: {response.text}')

if __name__ == '__main__':
    app.run()
