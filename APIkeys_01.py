from flask import request

# Keys with limited access to the API
trial_api_keys = {
    'trial_user': 'trial_key_198420'
}
def validate_trial_key(api_key):
    return api_key in trial_api_keys.values()

#------------------------------------------------------------

# Keys with full access to the API
full_api_keys = {
    'peterlehner': 'deepwellfarm'
}
def validate_full_key(api_key):
    return api_key in full_api_keys.values()

#------------------------------------------------------------

# Helper functions
def get_api_key():
    return request.headers.get('X-API-Key') #User must set in header under "X-API-Key"

def unauthorized():
    return "Unauthorized: Invalid API key", 401
