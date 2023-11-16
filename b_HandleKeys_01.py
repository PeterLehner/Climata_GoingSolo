from flask import request

# Full access to the API
full_keys = {
    'peterlehner': 'deepwellfarm'}

# Limited access to the API
trial_keys = {
    'trial_user': 'trial_key_142'}

def validate_key():
    path = request.path  # e.g., /v1/full or /v1/trial
    dictionary_to_search = full_keys if path.endswith('full') else trial_keys 
    api_key = request.headers.get('X-API-Key') #User must set in header under "X-API-Key"
    if api_key not in dictionary_to_search.values():
        return "Unauthorized: Invalid API key", 401
    return True