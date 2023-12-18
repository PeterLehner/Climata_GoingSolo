from flask import request

APIkeys = {
    'peterlehner': 'deepwellfarm',
    'bhr': 'cc58c18c-aafe-4522-9d23-5b72d48f2e32'
    }

def validate_key():
    #path = request.path  # e.g., /v1/full or /v1/trial
    #dictionary_to_search = full_keys if path.endswith('full') else trial_keys 
    api_key = request.headers.get('X-API-Key') #User must set in header under "X-API-Key"
    if api_key not in APIkeys.values():
        return "Unauthorized: Invalid API key", 401
    return True