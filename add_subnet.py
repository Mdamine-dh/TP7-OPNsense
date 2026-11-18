
import os
import requests
from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv("OPNSENSE_HOST")
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

url = f"{HOST}/api/kea/dhcpv4/add_subnet"

payload = {
    "subnet4": {
        "subnet": "192.168.50.0/24",
        "pools": "192.168.50.100 - 192.168.50.200",
        "option_data_autocollect": "0",
        "option_data": {
            "routers": "192.168.50.1",
            "domain_name_servers": "192.168.50.1"
        },
        "description": "LAN DHCP - Zero Touch"
    }
}

try:
    response = requests.post(
        url,
        json=payload,
        auth=(API_KEY, API_SECRET),
        verify=False,
        timeout=10
    )

    print("HTTP Status:", response.status_code)
    print("Response:", response.text)

except requests.exceptions.RequestException as error:
    print("Error:", error)
