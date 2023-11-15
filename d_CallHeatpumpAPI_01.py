import requests
import json
import time

zip_query = 39307
sqft = 1999
natgas_price_USD_per_1000_cf_2021 = 16.31
electricity_price = 0.12

def call_heapump_api(zip_query, sqft, electricity_price, natgas_price_USD_per_1000_cf_2021):
    zip_query = str(zip_query).zfill(5) #convert zip_query to string with 5 digits
    
    #create a new blank column in df_working
    status_quo_electricity_cooling = None
    status_quo_natgas              = None
    heatpump_electricity           = None

    KELVIN_API_start_time = time.time()

    url = "https://api.heatpumpshooray.com/kelvin/products"
    payload = json.dumps({
        "address"            : zip_query,
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

        status_quo_electricity_cooling = None
        status_quo_natgas = None
        for i in range(len(obj["status_quo"]["fuel_usage"])):
            if obj["status_quo"]["fuel_usage"][i]["type"] == "electricity":
                status_quo_electricity_cooling = obj["status_quo"]["fuel_usage"][i]["amount"]
                status_quo_electricity_cooling = round(status_quo_electricity_cooling, 0)
            if obj["status_quo"]["fuel_usage"][i]["type"] == "natural_gas":
                status_quo_natgas = obj["status_quo"]["fuel_usage"][i]["amount"]
                status_quo_natgas = round(status_quo_natgas, 0)

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
    except:
        print(f'API error: zip code {zip_query}')

    cost_before_heatpump = status_quo_electricity_cooling * electricity_price + status_quo_natgas * natgas_price_USD_per_1000_cf_2021/10 #Divide by 10 to convert to $/100cf
    cost_after_heatpump = heatpump_electricity * electricity_price
    heatpump_savings = cost_before_heatpump - cost_after_heatpump

    hp_run_time = time.time()-KELVIN_API_start_time
    
    #round to nearest integer
    status_quo_electricity_cooling = round(status_quo_electricity_cooling)
    status_quo_natgas              = round(status_quo_natgas)
    cost_before_heatpump           = round(cost_before_heatpump)
    heatpump_electricity           = round(heatpump_electricity)
    cost_after_heatpump            = round(cost_after_heatpump)  
    heatpump_savings               = round(heatpump_savings)
    hp_run_time                    = round(hp_run_time, 2)

    print(status_quo_electricity_cooling, status_quo_natgas, cost_before_heatpump, heatpump_electricity, cost_after_heatpump, heatpump_savings)
    print(f'Heatpump API run time: {hp_run_time} seconds')

    return status_quo_electricity_cooling, status_quo_natgas, cost_before_heatpump, heatpump_electricity, cost_after_heatpump, heatpump_savings

if __name__ == '__main__':
   
    result_tuple = call_heapump_api(zip_query, sqft, electricity_price, natgas_price_USD_per_1000_cf_2021)
    
    status_quo_electricity_cooling = result_tuple[0]
    status_quo_natgas              = result_tuple[1]
    cost_before_heatpump           = result_tuple[2]
    heatpump_electricity           = result_tuple[3]
    cost_after_heatpump            = result_tuple[4]
    heatpump_savings               = result_tuple[5]
    
    print(status_quo_electricity_cooling, status_quo_natgas, cost_before_heatpump, heatpump_electricity, cost_after_heatpump, heatpump_savings)