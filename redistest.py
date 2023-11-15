from flask import Flask, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from APIkeys_01 import validate_trial_key, validate_full_key
from CallModel_01 import CallModel
import os
import redis
import limits.storage

app = Flask(__name__)


REDIS_USERNAME = "red-cl9tkmto7jlc73fjaeog"
REDIS_PASSWORD = "P4Eh45g8zA2NUcBbDvdLV3nXs5bGuyEI"
REDIS_HOST = "oregon-redis.render.com"
REDIS_PORT = "6379"
REDIS_RENDER_URL = "redis://red-cl9tkmto7jlc73fjaeog:6379"
REDIS_LOCAL_URL = "rediss://red-cl9tkmto7jlc73fjaeog:P4Eh45g8zA2NUcBbDvdLV3nXs5bGuyEI@oregon-redis.render.com:6379"

redis_url = REDIS_LOCAL_URL

# Connect to your internal Redis instance using the REDIS_URL environment variable
# The REDIS_URL is set to the internal Redis URL e.g. redis://red-343245ndffg023:6379
#r = redis.from_url(os.environ['REDIS_URL'])
# r = redis.from_url(redis_url)
# r.set('key', 'redis-py')
# r.get('key')

# Initialize a Redis connection
redis_connection = redis.from_url(redis_url)


# Check Redis connection status
try:
    redis_connection.ping()  # Try to ping Redis to check the connection
    print("\nConnected to Redis successfully!")
except redis.ConnectionError as e:
    print(f"Error connecting to Redis: {e}")

limiter = Limiter(
  get_remote_address,
  app=app,
  default_limits=["1000 per day", "100 per hour"],
  storage_uri=redis_url,
  storage_options={"socket_connect_timeout": 30},
  strategy="fixed-window", # or "moving-window"
)
print("Storage URI used by Limiter:", limiter.storage)

limiter_storage = limiter._storage_uri
print("Limiter storage:", limiter_storage)

if isinstance(limiter.storage, redis.StrictRedis):  # Check if the storage is a Redis instance
    print("\nLimiter is using Redis as the storage URI.")
    # You can also perform further checks or access Redis properties if needed
else:
    print("\nLimiter is NOT using Redis as the storage URI.\n")


options = {}
redis_storage = limits.storage.storage_from_string(REDIS_LOCAL_URL, **options)
print("Redis storage:", redis_storage)
