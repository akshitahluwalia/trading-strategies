import upstox_client
from upstox_client.rest import ApiException
from urllib.parse import urlparse, parse_qs

API_VERSION = "v2"
API_KEY = "45a560fd-65cc-46df-bf70-82c692698188"
API_SECRET = "hwijgmi6cs"
REDIRECT_URL = "https://testadbfo.com/upstox/login/callback"
POSTBACK_URL = "https://testadbfo.com/upstox/postback"
CUSTOM_STATE = "CUSTOM-STATE-VALUE"
AUTHORIZATION_URL = f"https://api.upstox.com/{API_VERSION}/login/authorization/dialog?response_type=code&client_id={API_KEY}&redirect_uri={REDIRECT_URL}&state={CUSTOM_STATE}"

print(F">>>> Navigate to the following link for authorization :: {AUTHORIZATION_URL}")

REDIRECT_REQUEST = input(">>>> Please enter the Redirect URL :: ")
PARSED_URL = urlparse(REDIRECT_REQUEST)
AUTHORIZATION_CODE = parse_qs(PARSED_URL.query)['code'][0]
API_INSTANCE = upstox_client.LoginApi()
GRANT_TYPE = "authorization_code"

try:
    API_RESPONSE = API_INSTANCE.token(API_VERSION, code=AUTHORIZATION_CODE, client_id=API_KEY, client_secret=API_SECRET, redirect_uri=REDIRECT_URL, grant_type=GRANT_TYPE)
    print(API_RESPONSE)
    print("######## Access Token ########")
    print(API_RESPONSE.access_token)
except ApiException as e:
    print("#### EXCEPTION OCCURED ####")
    print(e)