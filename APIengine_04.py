from flask import Flask, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from APIkeys_01 import validate_trial_key, validate_full_key
from CallModel_01 import CallModel_01
import os
import redis

# Connect to your internal Redis instance using the REDIS_URL environment variable
# The REDIS_URL is set to the internal Redis URL e.g. redis://red-343245ndffg023:6379
REDIS_RENDER = "redis://red-cl9tkmto7jlc73fjaeog:6379"
REDIS_LOCAL  = "rediss://red-cl9tkmto7jlc73fjaeog:P4Eh45g8zA2NUcBbDvdLV3nXs5bGuyEI@oregon-redis.render.com:6379"
redis_url = REDIS_LOCAL
redis_connection = redis.from_url(redis_url)
try:
    redis_connection.ping()
    print("Connected to Redis successfully!")
except redis.ConnectionError as e:
    print(f"Error connecting to Redis: {e}")

app = Flask(__name__)

limiter = Limiter(
  get_remote_address,
  app=app,
  default_limits=["1000 per day", "1000 per hour"],
  storage_uri=redis_url,
  storage_options={"socket_connect_timeout": 30},
  strategy="fixed-window", # or "moving-window"
)


#Print limiter storage info
print(limiter.storage)

@app.route('/v1/trial', methods=['GET'])
@limiter.limit("2 per hour") #has to go after the route decorator
def trial_endpoint():
    api_key = request.headers.get('X-API-Key')
    if not api_key or not validate_trial_key(api_key):
        return "Unauthorized: Invalid API key", 401 
    return CallModel_01()

@app.route('/v1/full', methods=['GET'])
@limiter.limit("1000 per hour") #has to go after the route decorator
def full_endpoint():
    api_key = request.headers.get('X-API-Key')
    if not api_key or not validate_full_key(api_key):
        return "Unauthorized: Invalid API key", 401 
    return CallModel_01()


if __name__ == '__main__':
    app.run(debug=True)