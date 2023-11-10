import pandas as pd

ENERGY_PRICE_GROWTH_RATE = 1.022
NET_SAVINGS_YEARS = 20

BATTERY_COUNT = 1
BATTERY_KWH   = 13.5 # Tesla Powerwall capacity
BATTERY_KW    = 5 # Tesla Powerwall real power, KW, max continuous (charge and discharge)
BATTERY_KWH   = BATTERY_KWH * BATTERY_COUNT
BATTERY_KW    = BATTERY_KW * BATTERY_COUNT

def SavingsModel(zip_query, electric_bill_query, sqft_query, heatpump_query): 
    df_working = pd.read_csv('Data/database_main.csv')
    zip_query = int(zip_query)  # Convert to integer
    dict_working = df_working[df_working['zip'] == zip_query].squeeze().to_dict()  # Read the row with the matching zip_query as a dictionary

    avg_electricity_use_kwh = dict_working.get('avg_electricity_use_kwh')
    electricity_price       = dict_working.get('electricity_price')
    output_annual           = dict_working.get('output_annual')
    sizing_ratio            = dict_working.get('sizing_ratio')
    net_metering            = dict_working.get('net_metering')



    # if electric_bill_query is not None:
    #     electricity_use_kwh = (12*electric_bill_query)/electricity_price #Calcuate a homeowners electric use based on their electric bill.
    # else:
    #     electricity_use_kwh = avg_electricity_use_kwh # Else, use the average electric use for the zip code


    electricity_use_kwh = (12*electric_bill_query)/electricity_price #Calcuate a homeowners electric use based on their electric bill.

    recommended_system_size_KW = electricity_use_kwh * sizing_ratio # e.g.: ~10,000 KWH * (1 KW / ~1000 KWH) = ~10 KW
       
    year1_production_savings = electricity_use_kwh * electricity_price








    # Round the variables with inline if statements
    electricity_use_kwh         = round(electricity_use_kwh) if electricity_use_kwh is not None else electricity_use_kwh
    recommended_system_size_KW  = round(recommended_system_size_KW, 1) if recommended_system_size_KW is not None else recommended_system_size_KW
    #system_output_annual        = round(system_output_annual) if system_output_annual is not None else system_output_annual
    
    net_metering                = round(net_metering) if net_metering is not None else net_metering
    year1_production_savings    = round(year1_production_savings) if year1_production_savings is not None else year1_production_savings
    #NetMetering_eligible_production = round(NetMetering_eligible_production) if NetMetering_eligible_production is not None else NetMetering_eligible_production
    electricity_price           = round(electricity_price, 3) if electricity_price is not None else electricity_price
    


    if year1_production_savings > 1799 and year1_production_savings < 1801:
        print("\nelectric_bill_query: ", electric_bill_query)
        print("net_metering: ", net_metering)
        print("electricity_price: ", electricity_price)
        print("recommended_system_size_KW: ", recommended_system_size_KW)
        print("electricity_use_kwh: ", electricity_use_kwh)
        #print("system_output_annual: ", system_output_annual)
        #print("NetMetering_eligible_production: ", NetMetering_eligible_production)
        
        #print("\nyear1_production_savings: ", year1_production_savings)


    result_dict = {
        'zip_query'                  : zip_query,
    }
    if year1_production_savings < 1799 or year1_production_savings > 1801:
        result_dict = None
    return result_dict