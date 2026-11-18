
import os
import requests
from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv("OPNSENSE_HOST")
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

url = f"{HOST}/api/kea/dhcpv4/get"

try:
    response = requests.get(
        url,
        auth=(API_KEY, API_SECRET),
        verify=False,
        timeout=10
    )

    print("HTTP Status:", response.status_code)
    print("DHCP Configuration:")
    print(response.text)

except requests.exceptions.RequestException as error:
    print("Error:", error)
