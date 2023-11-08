import requests
import json
import pandas as pd
import time

def CallHeatPumpAPI():
    df_working = pd.read_csv('0_output.csv')

    df_zip_to_median_sqft = pd.read_csv('/Users/peterlehner/Dropbox/Climata_nonGit/Data/Square footage/zip_to_median_sqft.csv') # read in zip_to_median_sqft.csv

    #Create a new dataframe that group df_zip_to_median_sqft by the 'state' column and takes the median_sqft
    df_state_to_median_sqft = df_zip_to_median_sqft.groupby('state')['median_sqft'].median().reset_index()
    df_state_to_median_sqft = df_state_to_median_sqft.rename(columns={'median_sqft': 'median_sqft_state'})

    df_zip_to_median_sqft = df_zip_to_median_sqft[['zip', 'median_sqft']] # drop all columns except zip and median_sqft so that we don't end up with duplicate state columsn after merge
    df_working = pd.merge(df_working, df_zip_to_median_sqft, left_on='zip', right_on='zip', how='left')     # merge df_working with df_zip_to_median_sqft

    # drop zip column
    #df_working = df_working.drop(columns=['zip'])

    df_working = pd.merge(df_working, df_state_to_median_sqft, left_on='state', right_on='state', how='left')

    print(df_working.head())

    # if median_sqft is null, replace with median_sqft_state
    df_working['median_sqft'] = df_working['median_sqft'].fillna(df_working['median_sqft_state'])

    # round median_sqft to nearest 1
    df_working['median_sqft'] = df_working['median_sqft'].round(0)
    
    #create a new blank column in df_working
    df_working['status_quo_electricity'] = None
    df_working['status_quo_natgas'] = None
    df_working['heatpump_electricity'] = None

    KELVIN_API_start_time = time.time()

    for z in range(len(df_working)):
        df_working['zip'] = df_working['zip'].apply(str).str.zfill(5)
        zip = df_working['zip'][z]
        sqft = df_working['median_sqft'][z]
        print(f'Heat pump API: {z} of {len(df_working)}: {zip}')

        url = "https://api.heatpumpshooray.com/kelvin/products"

        payload = json.dumps({
          "address"            : zip,
          "sqft"               : sqft,
          "ceiling_height"     : 9,
          "stories"            : 2,
          "windows"            : 0.2,
          "shape"              : 1,
          "occupants"          : 4,
          "therm_heat"         : 70,
          "therm_cool"         : 75,
          "zones"              : 2,
          "envelope_multiplier": 0.65,
          "solar_multiplier"   : 1.25,
          "heating_fuel"       : "natural_gas",
          "heating_afue"       : 80,
          "cooling_seer"       : 14
        })
        headers = {
          'Content-Type': 'application/json'
        }

        try:
            response = requests.request("POST", url, headers=headers, data=payload)
            response_json = response.text
            obj = json.loads(response_json)

            status_quo_electricity = None
            status_quo_natgas = None
            for i in range(len(obj["status_quo"]["fuel_usage"])):
              if obj["status_quo"]["fuel_usage"][i]["type"] == "electricity":
                  status_quo_electricity = obj["status_quo"]["fuel_usage"][i]["amount"]
                  status_quo_electricity = round(status_quo_electricity, 0)
              if obj["status_quo"]["fuel_usage"][i]["type"] == "natural_gas":
                  status_quo_natgas = obj["status_quo"]["fuel_usage"][i]["amount"]
                  status_quo_natgas = round(status_quo_natgas, 0)

            #add status quo to dataframe
            df_working.loc[z, 'status_quo_electricity'] = status_quo_electricity
            df_working.loc[z, 'status_quo_natgas'] = status_quo_natgas

            heatpump_electricity_list = []
            heatpump_electricity = None
            for i in range(len(obj["products"])):
                if obj["products"][i]["evaluation"]["recommended"] == True:
                    for j in range(len(obj["products"][i]["performance"]["fuel_usage"])):
                        if obj["products"][i]["performance"]["fuel_usage"][j]["type"] == "electricity":
                            heatpump_electricity = obj["products"][i]["performance"]["fuel_usage"][j]["amount"]
                            heatpump_electricity = round(heatpump_electricity, 0)
                            heatpump_electricity_list.append(heatpump_electricity)

            #Find miniumum electricity usage
            heatpump_electricity = min(heatpump_electricity_list)
            df_working.loc[z, 'heatpump_electricity'] = heatpump_electricity
        except:
            print(f'API error: zip Code {zip}')

        print(f'\n{z+1} of {len(df_working)}')
        print(f'{round(z/len(df_working)*100, 1)}% complete')
        print(f'{round((time.time()-KELVIN_API_start_time)/60, 2)} minutes since start of KELVIN API calls')

    #Read in state level nat gas prices
    df_natgas_prices = pd.read_csv('/Users/peterlehner/Dropbox/Climata_nonGit/Data/Energy/state_to_avg_natgas_price.csv')
    df_working = pd.merge(df_working, df_natgas_prices, left_on='state', right_on='state', how='left')

    df_working['cost_before_heatpump'] = df_working["status_quo_electricity"] * df_working['electricity_price'] + df_working["status_quo_natgas"] * df_working['natgas_price_$_per_1000_cf_2021']/10 #Divide by 10 to convert to $/100cf
    df_working['cost_after_heatpump'] = df_working["heatpump_electricity"] * df_working['electricity_price']
    df_working['heatpump_savings'] = df_working['cost_before_heatpump'] - df_working['cost_after_heatpump']

    print(df_working['heatpump_savings'])

    df_working.to_csv('0_output.csv', index=False)
    print('\nCallHeatPumpAPI: 0_output\n')

if __name__ == '__main__':
    CallHeatPumpAPI()