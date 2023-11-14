# Dictionary of API keys. User must set in header under "X-API-Key"
trial_api_keys = {
    'trial_user': 'trial_key_198420'
}

def validate_trial_key(api_key):
    return api_key in trial_api_keys.values()


full_api_keys = {
    'peterlehner': 'deepwellfarm'
}

def validate_full_key(api_key):
    return api_key in full_api_keys.values()