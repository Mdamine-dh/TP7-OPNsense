
import os
import requests
from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv("OPNSENSE_HOST")
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
VERIFY_SSL = os.getenv("VERIFY_SSL", "true").lower() == "true"

url = f"{HOST}/api/core/firmware/status"

try:
    response = requests.get(
        url,
        auth=(API_KEY, API_SECRET),
        verify=VERIFY_SSL,
        timeout=10
    )

    print("HTTP Status:", response.status_code)
    print("Response:", response.text)

except requests.exceptions.RequestException as error:
    print("Connection error:", error)
