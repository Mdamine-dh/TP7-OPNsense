
import os
import requests
from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv("OPNSENSE_HOST")
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
VERIFY_SSL = os.getenv("VERIFY_SSL", "true").lower() == "true"

url = f"{HOST}/api/firewall/d_nat/add_rule"

payload = {
    "rule": {
        "sequence": "200",
        "disabled": "0",
        "nordr": "0",
        "interface": ["wan"],
        "ipprotocol": "inet",
        "protocol": "tcp",
        "source": {
            "network": "any",
            "address": "",
            "port": "",
            "not": "0"
        },
        "destination": {
            "network": "wanip",
            "address": "",
            "port": "8080",
            "not": "0"
        },
        "target": "192.168.50.100",
        "local-port": "8080",
        "natreflection": "",
        "pass": "pass",
        "descr": "TP7 - Web Server Port Forward"
    }
}

response = requests.post(
    url,
    auth=(API_KEY, API_SECRET),
    json=payload,
    verify=VERIFY_SSL,
    timeout=15
)

print("HTTP Status:", response.status_code)
print("Response:", response.text)