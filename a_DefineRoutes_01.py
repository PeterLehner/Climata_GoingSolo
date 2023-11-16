from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from b_HandleKeys_01 import validate_trial_key, validate_full_key, get_api_key, unauthorized
#from b_HandleQuery_01 import handle_query
from b_HandleQuery_02 import handle_query
import os

app = Flask(__name__)

# Setting up redis instance for rate limiting and defining the limiter
REDIS_ON_RENDER = "redis://red-cl9tkmto7jlc73fjaeog:6379"
REDIS_ON_MAC    = "rediss://red-cl9tkmto7jlc73fjaeog:P4Eh45g8zA2NUcBbDvdLV3nXs5bGuyEI@oregon-redis.render.com:6379"
redis_url = REDIS_ON_RENDER if os.getenv('on_render_check') == 'true' else REDIS_ON_MAC
print(f"\nredis_url: {redis_url}\n")

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["1000 per day", "1000 per hour"],
    storage_uri=redis_url,
    storage_options={"socket_connect_timeout": 30},
    strategy="fixed-window",
)


@app.route('/v1/full', methods=['GET'])
def full_endpoint_v1():
    api_key = get_api_key()
    if not validate_full_key(api_key):
        return unauthorized()
    return handle_query()

@app.route('/v1/trial', methods=['GET'])
@limiter.limit("2 per hour")
def trial_endpoint_v2():
    api_key = get_api_key()
    if not validate_trial_key(api_key):
        return unauthorized()
    return handle_query()


if __name__ == '__main__':
    debug_state = False if os.getenv('on_render_check') == 'true' else True    
    app.run(debug=debug_state)