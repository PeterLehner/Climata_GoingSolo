import requests
import json
import pandas as pd
import time

def MergeCachedKelvinOutput():
    df_working = pd.read_csv('0_output.csv')

    #Read in state level nat gas prices
    df_natgas_prices = pd.read_csv('/Users/peterlehner/Dropbox/Climata_nonGit/Data/Energy/state_to_avg_natgas_price.csv')
    df_working = pd.merge(df_working, df_natgas_prices, left_on='state', right_on='state', how='left')

    #Read in cached Kelvin API results. Note: these use zip or state level average square footage
    df_cached_kelvin = pd.read_csv('/Users/peterlehner/Dropbox/Climata_nonGit/Data/Kelvin/Kelvin_API_cached.csv')
    df_cached_kelvin = df_cached_kelvin[['zip', 'status_quo_electricity', 'status_quo_natgas', 'heatpump_electricity']] #only keep relevant columns (ignore state and sqft)

    df_working = pd.merge(df_working, df_cached_kelvin, left_on='zip', right_on='zip', how='left')

    df_working['cost_before_heatpump'] = df_working["status_quo_electricity"] * df_working['electricity_price'] + df_working["status_quo_natgas"] * df_working['natgas_price_$_per_1000_cf_2021']/10 #Divide by 10 to convert to $/100cf
    df_working['cost_after_heatpump'] = df_working["heatpump_electricity"] * df_working['electricity_price']

    df_working['heatpump_savings'] = df_working['cost_before_heatpump'] - df_working['cost_after_heatpump']

    df_working.to_csv('0_output.csv', index=False)
    print('MergeCachedKelvinOutput: 0_output\n')

if __name__ == '__main__':
    MergeCachedKelvinOutput()