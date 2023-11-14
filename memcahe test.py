import os
from flask import Flask
import memcache
from pymemcache.client.base import Client as MemcacheClient


app = Flask(__name__)

# Retrieve Memcached connection details from environment variables
memcached_host = os.environ.get('MEMCACHED_HOST')
memcached_port = int(os.environ.get('MEMCACHED_PORT'))  # Convert port to integer
memcached_username = os.environ.get('MEMCACHED_USERNAME')
memcached_password = os.environ.get('MEMCACHED_PASSWORD')

print(f"Memcached host: {memcached_host}")

# Create Memcached client
mc = MemcacheClient((memcached_host, memcached_port))

# Example route to set and get a value from Memcached
@app.route('/')
def index():
    mc.set("key", "value")
    result = mc.get("key")
    return f"Value from Memcached: {result.decode('utf-8') if result else 'Not found'}"

if __name__ == '__main__':
    app.run(debug=True)
