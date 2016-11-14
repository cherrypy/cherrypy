import requests
import json

def sendHttpPatch():
    info = {
        'last_name' : 'Smith',   
    }

    bodyData = json.dumps(info)
    print(bodyData)

    r = requests.patch('http://localhost:8080/api/users/123-456-789', data=None, json=bodyData)
    print(r.status_code)
    print(r.json())

sendHttpPatch()

