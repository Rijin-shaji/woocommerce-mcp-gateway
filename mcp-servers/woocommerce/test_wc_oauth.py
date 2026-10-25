import os
import requests
from requests_oauthlib import OAuth1
from dotenv import load_dotenv

load_dotenv()

base_url = os.getenv("WOOCOMMERCE_URL", "").rstrip("/")
consumer_key = os.getenv("WOOCOMMERCE_CONSUMER_KEY")
consumer_secret = os.getenv("WOOCOMMERCE_CONSUMER_SECRET")

auth = OAuth1(
    consumer_key,
    consumer_secret,
    signature_method="HMAC-SHA1",
)

url = f"{base_url}/products"
response = requests.get(
    url,
    params={"per_page": 1},
    auth=auth,
    timeout=15,
)

print("HTTP status:", response.status_code)
print("Response:", response.text[:700])