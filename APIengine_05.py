from flask import Flask, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from APIkeys_01 import validate_trial_key, validate_full_key, get_api_key, unauthorized
from CallModel_01 import CallModel_01
import os
import redis

app = Flask(__name__)

#----------------v1/full

@app.route('/v1/full', methods=['GET'])
def full_endpoint_v1():
    api_key = get_api_key()
    if not validate_full_key(api_key):
        return unauthorized()
    return CallModel_01()

#----------------v1/trial

REDIS_ON_RENDER = "redis://red-cl9tkmto7jlc73fjaeog:6379"
REDIS_ON_MAC = "rediss://red-cl9tkmto7jlc73fjaeog:P4Eh45g8zA2NUcBbDvdLV3nXs5bGuyEI@oregon-redis.render.com:6379"
redis_url = REDIS_ON_RENDER if os.getenv('on_render_check') == 'true' else REDIS_ON_MAC
print(f"\nredis_url: {redis_url}\n")
# redis_connection = redis.from_url(redis_url)
# try:
#     redis_connection.ping()
#     print("\nConnected to Redis successfully\n")
# except redis.ConnectionError as e:
#     print(f"\nError connecting to Redis: {e}\n")

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["1000 per day", "1000 per hour"],
    storage_uri=redis_url,
    storage_options={"socket_connect_timeout": 30},
    strategy="fixed-window",
)

@app.route('/v1/trial', methods=['GET'])
@limiter.limit("2 per hour")
def trial_endpoint_v2():
    api_key = get_api_key()
    if not validate_trial_key(api_key):
        return unauthorized()
    return CallModel_01()

if __name__ == '__main__':
    app.run(debug=True)