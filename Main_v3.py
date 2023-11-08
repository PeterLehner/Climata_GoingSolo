import pandas as pd
import requests
import numpy as np
import json
import time
from Heatpumps import CallHeatPumpAPI
from MergeCachedKelvinOutput import MergeCachedKelvinOutput

def SelectZipCodes(): # done
    INPUT_DF = pd.read_csv('/Users/peterlehner/Dropbox/Climata_GoingSolo/Data/Zips/zip_lat_lon_state.csv')
    #INPUT_DF = pd.read_csv('/Users/peterlehner/Dropbox/Climata_GoingSolo/USB_zips.csv')
    #INPUT_DF = pd.read_csv('/Users/peterlehner/Library/CloudStorage/Dropbox/Climata_GoingSolo/Data/Zips/HSFCU_zips.csv')

    INPUT_DF = INPUT_DF[INPUT_DF['state'].isin(APPLICAPLE_STATES)] # Only keep zips in states relevant to the selected bank
    
    INPUT_DF['zip'] = [str(x).zfill(5) for x in INPUT_DF['zip']] # Make all zips string and 5 characters

    # TEMP_CODE #32073
    #INPUT_DF = INPUT_DF[INPUT_DF['zip'].isin(['33188'])] # Only keep zips in states relevant to the selected bank

    #Take the first N rows of the input file
    if TAKE_SAMPLE == True:
        INPUT_DF = INPUT_DF.head(NUMBER_OF_ZIPS)
    
    #INPUT_DF = INPUT_DF.sample(n=NUMBER_OF_ZIPS, random_state=1) # Randomly select zip codes from input file
    print(len(INPUT_DF))
    INPUT_DF.to_csv('0_zips_to_run.csv', index=False)
    print('SelectZipCodes: 0_zips_to_run.csv\n')

def CallSolarAPI(): # done
    df_pvwatts_input = pd.read_csv('0_zips_to_run.csv')

    zip_codes_out = []
    latitudes = []
    longitudes = []
    states = []
    tilts = []
    directions = []
    output_annuals = []
    capacity_factors = []
    zipcodes_FAILED = []

    #NREL PVWatts API access
    URL = "https://developer.nrel.gov/api/pvwatts/v8.json?" # Go to this link to see a descripton of every input and output field: https://developer.nrel.gov/docs/solar/pvwatts/v8/
    API_KEY = "E6Sl19hiIiLDfCugsqDPCJxEqOuhElKmPKK6BD5J"
    
    print(f'Number of zip codes to run: {len(df_pvwatts_input)}\n')

    #mark the start time
    NREL_API_start_time = time.time()

    for l in range(len(df_pvwatts_input)):
        zip_code = df_pvwatts_input.at[l,'zip']
        lat      = df_pvwatts_input.at[l,'lat']
        lon      = df_pvwatts_input.at[l,'lon']
        state    = df_pvwatts_input.at[l,'state']
        tilt     = lat #in case the API call fails, we still want to have the tilt
        direction= 180 #in case the API call fails, we still want to have the direction
        
        parameters = {
            "api_key":     API_KEY, 
            "system_capacity":   1, #Nameplate capacity (kW)
            "module_type":     "0", #Module type. 0=Standard 1=Premium 2=Thin film
            "losses":         "14", #System losses (percent). Back out what the system losses are from Energy Sage?
            "array_type":      "1", #0=Fixed - Open Rack, 1=Fixed - Roof Mounted, 2=1-Axis 3=1-Axis Backtracking, 4=2-Axis
            "tilt":            lat, #Tilt angle (degrees) # USE THE LATITUDE
            "azimuth":         180, #direction that the panel faces. I think north is 0
            "lat":             lat,
            "lon":             lon, 
            "dataset":     "nsrdb", #The climate dataset to use
            "radius":          "0", #The search radius to use when searching for the closest climate data station (miles). Pass in radius=0 to use the closest station regardless of the distance.
            "timeframe": "monthly",
            "dc_output_ratio":   "1.2", #DC to AC ratio
            "gcr":           "0.4", #Ground coverage ratio
            "inv_eff":      "96.0", #Inverter efficiency at rated power
            #"address": city_state, #The address to use. Required if lat/lon or file_id not specified
            "SOILING": [SOILING,SOILING,SOILING,SOILING,SOILING,SOILING,SOILING,SOILING,SOILING,SOILING,SOILING,SOILING] # Reduction in incident solar irradianceSpecify a pipe-delimited array of 12 monthly values.
            }
        try:
            response = requests.request("GET", URL, params = parameters)
        except:
            print('API call failed')
            zipcodes_FAILED.append(zip_code)
            continue
        if response.status_code != 200:
            print(response)
            zipcodes_FAILED.append(zip_code)
            output_annual = 'fail'
            capacity_factor = 'fail'
            calls_remaining = 999999
        #pretty_print_response(response) #uncomment this line to see the full response

        try:
            j = response.json()
            calls_remaining = response.headers['X-Ratelimit-Remaining']
        
            tilt              = j['inputs']['tilt']
            direction         = j['inputs']['azimuth']
            lat               = j['station_info']['lat']
            lon               = j['station_info']['lon']
            output_annual     = j['outputs']['ac_annual']
            capacity_factor   = j['outputs']['capacity_factor']
            print(f'output_annual: {output_annual}')
        except:
            zipcodes_FAILED.append(zip_code)
            output_annual = 0
            capacity_factor = 0
                                
        if output_annual != 'fail':
            output_annual = round(output_annual)
            capacity_factor = round(capacity_factor, 3)
    
        zip_codes_out.append(zip_code)
        states.append(state)
        latitudes.append(lat)
        longitudes.append(lon)
        tilts.append(tilt)
        directions.append(direction)
        output_annuals.append(output_annual)
        capacity_factors.append(capacity_factor)
        
        print(f'{l+1} of {len(df_pvwatts_input)}')
        print(f'{round(l/len(df_pvwatts_input)*100, 1)}% complete')
        print(f'{round((time.time()-NREL_API_start_time)/60, 2)} minutes since start of NREL API calls')
        print(f'{round((len(df_pvwatts_input)-l)*5/3600, 2)} hours remaining')

        print(f'Zip code:        {zip_code}')              
        print(f'Calls remaining: {calls_remaining}\n')
        #keep track of what percent of the zip codes have been run

        if RUNTIME_DELAY == True:
            time.sleep(3.8) #Hourly Limit: 1,000 requests per hour. "Exceeding these limits will lead to your API key being temporarily blocked from making further requests. The block will automatically be lifted by waiting an hour"
        
        if int(calls_remaining) < 30: #NREL rate limits the API to 1000 calls / hour. Refreshes on a rolling basis. 
            print("Sleeping...")
            time.sleep(10.0)

    #create dataframe from lists
    data = {'zip':zip_codes_out,
         'lat': latitudes,
         'lon': longitudes,
         'state': states,
         'output_annual': output_annuals}
    df_working = pd.DataFrame(data)
    
    df_working.to_csv('0_output.csv', index=False)
    print('CallSolarAPI: 0_output\n')

def MergeCachedNRELoutput(): # TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO
    df_pvwatts_input = pd.read_csv('0_zips_to_run.csv')

    #merge df_pvwatts_input with Output_annual_WAORCANVNYNJPA.csv on "zip"
    df_output_annual = pd.read_csv('/Users/peterlehner/Dropbox/Climata_GoingSolo/Data/NREL/NREL_API_cache.csv')
    
    #only read in the columns we need
    df_output_annual = df_output_annual[['zip','output_annual']]

    #round output_annual to nearest integer
    df_output_annual['output_annual'] = df_output_annual['output_annual'].round(0)

    df_working = pd.merge(df_pvwatts_input, df_output_annual, left_on='zip', right_on='zip', how='left')

    #print name of function
    print('MergeCachedNRELoutput: 0_output\n')

    #export to csv
    df_working.to_csv('0_output.csv', index=False)

def MergeZipLevelDemand_OLD(): # done
    df_working = pd.read_csv('0_output.csv')
    df_working['zip'] = df_working['zip'].apply(str).str.zfill(5)

    df_electricity_prices = pd.read_csv('/Users/peterlehner/Dropbox/Climata_GoingSolo/Data/Energy/zip_to_avg_energy_bill.csv') #Read in zip level demand data   
    df_electricity_prices['zip'] = df_electricity_prices['zip'].apply(str).str.zfill(5) #clean up zip codes
    df_electricity_prices = df_electricity_prices.rename(columns = {'zip':'zip'}) # rename column to match df_working

    #merge dataframes. This merge adds columns: Average energy use (kWh) and Average Electricity Bill (USD)
    df_working = pd.merge(df_working, df_electricity_prices, left_on='zip', right_on='zip', how='left')
    df_working.drop(columns=['Random #'], inplace=True)
    df_working = df_working.rename(columns={'Average energy use (kWh)':'avg_electricity_use_kwh'})

    #calculate the price of energy in $/kWh for that zip code
    df_working['electricity_price'] = (12*df_working["avg_electric_bill_monthly"])/df_working['avg_electricity_use_kwh']

    df_working.to_csv('0_output.csv', index=False)
    print('MergeZipLevelDemand: 0_output\n')

def MergeZipLevelDemand(): # done
    df_working = pd.read_csv('0_output.csv')
    df_working['zip'] = df_working['zip'].apply(str).str.zfill(5)

    df_electricity_prices = pd.read_csv('/Users/peterlehner/Dropbox/Climata_GoingSolo/Data/Energy/zip_to_electricity_price.csv') #Read in zip level demand data   
    df_electricity_prices['zip'] = df_electricity_prices['zip'].apply(str).str.zfill(5) #clean up zip codes 
    df_working = pd.merge(df_working, df_electricity_prices, left_on='zip', right_on='zip', how='left')
    # Prices have gone up a lot since these prices were collected.  Therefore we should use them as a relative metric
    # EIA projects much higher prices for 2023 and 2024: https://www.eia.gov/outlooks/steo/report/electricity.php
    # Dividing their average by our average  $0.1565/$0.1185 = 1.32
    df_working['electricity_price'] = df_working['electricity_price'] * 1.32 # Account for 3 years of inflation 

    # # COUNTY LEVEL DEMAND - Seems iffy
    # df_electricity_demand = pd.read_csv('/Users/peterlehner/Dropbox/Climata_GoingSolo/Data/Energy/zip_to_county_to_electricity_demand.csv') #Read in zip level demand data   
    # df_electricity_demand = df_electricity_demand[['zip','avg_electricity_use_kwh']]
    # df_electricity_demand['zip'] = df_electricity_demand['zip'].apply(str).str.zfill(5) #clean up zip codes 
    # df_working = pd.merge(df_working, df_electricity_demand, left_on='zip', right_on='zip', how='left')

    # STATE LEVEL DEMAND - less precise, more smooth
    df_electricity_demand = pd.read_csv('/Users/peterlehner/Dropbox/Climata_GoingSolo/Data/Energy/state_to_avg_electricity_use.csv') #Read in zip level demand data   
    df_electricity_demand = df_electricity_demand[['state','avg_electricity_use_kwh']]

    #TEMP_CODE --- scaling up energy use in San Diego to reflect that fact that avg. solar size is 7.49 kw at a .195 CF (12794 = 7.49*8760*.195)
    # df_electricity_demand.loc[df_electricity_demand['state'] == 'CA', 'avg_electricity_use_kwh'] = 12794 # 7.71 
    # df_electricity_demand.loc[df_electricity_demand['state'] == 'TX', 'avg_electricity_use_kwh'] = 20156 # 12.98 
    # df_electricity_demand.loc[df_electricity_demand['state'] == 'AZ', 'avg_electricity_use_kwh'] = 21251 # 11.90 
    # df_electricity_demand.loc[df_electricity_demand['state'] == 'FL', 'avg_electricity_use_kwh'] = 21663 # 14.10 

    df_working = pd.merge(df_working, df_electricity_demand, left_on='state', right_on='state', how='left')

    df_working['avg_electric_bill_monthly'] = df_working['avg_electricity_use_kwh'] * df_working['electricity_price'] / 12

    df_working.to_csv('0_output.csv', index=False)
    print('MergeZipLevelDemand: 0_output\n')

def CalculateSizingRatio():    # done
    df_working = pd.read_csv('0_output.csv')

    df_working['sizing_ratio'] = 1/df_working['output_annual'] # Because output_annual here is the output for a 1 KW system.
    df_working['capacity_factor'] = df_working['output_annual']/8760 # Because output_annual here is the output for a 1 KW system, 8760 kwh is ideal

    df_working.to_csv('0_output.csv', index=False)
    print('CalculateSizingRatio: 0_output\n')

# Call CallHeatPumpAPI() # done
# Call MergeCachedKelvinOutput() # TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO

def CalculateRecommendedSystemSize(): # TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO
    df_working = pd.read_csv('0_output.csv')

    if net_of_heatpumps == True:
        df_working['avg_electricity_use_kwh'] = df_working['avg_electricity_use_kwh'] + df_working["heatpump_electricity"]
        df_working['Heat pump'] = 'Yes'
        df_working['avg_electric_bill_monthly'] = df_working['avg_electricity_use_kwh']*df_working['electricity_price']/12
    else:
        df_working['Heat pump'] = 'No'

    ############################## THIS IS WHERE THINGS DEVIATE BASED ON WHETHER THE STATE HAS NET METERING OR NOT ##############################

    #This file adds columns: state_name, climata_rank, percent_incentive_max_$, incentive_percent, net_of_federal, SREC_$_kwh, and net_metering
    df_incentives = pd.read_csv('/Users/peterlehner/Dropbox/Climata_GoingSolo/Data/Incentives/state_to_DSIRE_incentives_031823.csv')
    df_incentives = df_incentives[['state', 'net_metering']] # Drop all columns except state and net_metering
    df_working = pd.merge(df_working, df_incentives, on='state', how='left')

    #calculate how much to scale down the size of the solar array IF the system is paired with a battery (in the case of NO net metering)
    df_working['EnergyUse_to_BatterySize'] = df_working['avg_electricity_use_kwh']/(BATTERY_COUNT*13.5*1000) # 13.5 kWh is capacity of a Tesla Powerwall
    df_working['solarWbattery_system_scaling_factor'] = -0.2017*df_working['EnergyUse_to_BatterySize'] + 0.8646 # This linear equation from Battery_sensitivity_analysis.xlsx
    df_working.loc[df_working['net_metering'] == 1, 'solarWbattery_system_scaling_factor'] = 1 # if the value of df_working['net_metering'] == 1, then reset the scaling factor should be 1 (i.e., no scaling)

    #calculate the recommended system size in KW. This is the average energy use in the zip code * the sizing ratio and, IF the battery is included, the solarWbattery_system_scaling_factor
    df_working['recommended_system_size_(KW)'] = df_working['solarWbattery_system_scaling_factor']*df_working['avg_electricity_use_kwh']*df_working['sizing_ratio'] # e.g.: 10,000 KWH * (1 KW / 1000 KWH) = 10 KW.   10 KW * (1000 KWH / 1 KW) = 10,000 KWH

    #take the mininum of the recommended system size and 15 KW because roofs can't fit large arrays
    df_working['recommended_system_size_(KW)'] = df_working['recommended_system_size_(KW)'].apply(lambda x: min(x, 15))

    df_working['system_output_annual'] = df_working['recommended_system_size_(KW)']*df_working['output_annual']

    df_working.to_csv('1_output.csv', index=False)
    print('CalculateRecommendedSystemSize: 1_output\n')

def MergeCosts(): # done
    #df_working = pd.read_csv('1_output.csv')
    df_working = pd.read_csv('1_output.csv')

    #This file adds a column with the average price per KW for each state
    df_costs = pd.read_csv('/Users/peterlehner/Dropbox/Climata_GoingSolo/Data/Cost/state_to_cost_per_kw.csv', usecols=['state','avg_cost_per_kw'])

    df_working = pd.merge(df_working, df_costs, on='state', how='left')

    df_working['estimated_cost'] = df_working['avg_cost_per_kw']*df_working['recommended_system_size_(KW)']

    df_working.to_csv('1_output.csv', index=False)
    print('MergeCosts: 1_output\n')

def MergeIncentivesCalculateGrossSavings(): # TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO
    df_working = pd.read_csv('1_output.csv')

    print(df_working)

    #This file adds columns: state_name, climata_rank, percent_incentive_max_$, incentive_percent, net_of_federal, SREC_$_kwh, and net_metering
    df_incentives = pd.read_csv('/Users/peterlehner/Dropbox/Climata_GoingSolo/Data/Incentives/state_to_DSIRE_incentives_031823.csv')
    df_incentives.drop(columns=['state_name', 'climata_rank','net_metering'], inplace=True)

    df_working = pd.merge(df_working, df_incentives, on='state', how='left') 

    # --------------------------------------------- CALCULATE TAX REBATES AND INCENTIVES ---------------------------------------------
    
    # FEDERAL
    df_working['federal_incentive'] = 0.3*df_working['estimated_cost']

    #create a temporary column for the cost of the system NET of the federal tax credit (for applicable states, of course)
    for index, row in df_working.iterrows():
        #print(f'\nindex: {index}, row: {row}\n')
        if row['net_of_federal'] == 1:
            df_working.loc[index, 'temp_cost'] = row['estimated_cost']*.7
        else:
            df_working.loc[index, 'temp_cost'] = row['estimated_cost']
    
    #Calculate state incentive
    #First, calculate state incentive by percent of system cost
    for index, row in df_working.iterrows():
        if row['incentive_percent'] == 0:
            df_working.loc[index, 'state_incentive_by_percent'] = row['percent_incentive_max_$']
        elif row['percent_incentive_max_$'] == 0:
            df_working.loc[index, 'state_incentive_by_percent'] = row['incentive_percent']*row['temp_cost']
        else:
            df_working.loc[index, 'state_incentive_by_percent'] = min(row['incentive_percent']*row['temp_cost'], row['percent_incentive_max_$'])

    #Second, calculate state incentive by $ per W of installed capacity
    for index, row in df_working.iterrows():
        if row['incentive_per_W'] == 0: #if there is no incentive per KW, then just take the lump sum in the max column
            df_working.loc[index, 'state_incentive_by_W'] = row['W_incentive_max_$']
        elif row['W_incentive_max_$'] == 0: #if there is no max, just take the incentive per KW multiplied by the system size
            df_working.loc[index, 'state_incentive_by_W'] = row['incentive_per_W']*1000*row['recommended_system_size_(KW)']
        else: # there is both a max and a per KW incentive, so take the lower of the two
            df_working.loc[index, 'state_incentive_by_W'] = min(row['incentive_per_W']*1000*row['recommended_system_size_(KW)'], row['W_incentive_max_$'])

    df_working['net_estimated_cost'] = df_working['estimated_cost'] - df_working['federal_incentive'] - df_working['state_incentive_by_percent'] - df_working['state_incentive_by_W']
    df_working.drop(columns=['temp_cost'], inplace=True)

    # ILLINOIS has a complicated REC program where they prepurchase 15 years of recs. SOURCE: https://www.solarreviews.com/blog/illinois-renews-best-solar-incentive
    for index, row in df_working.iterrows():
        if row['state'] == 'IL' and row['recommended_system_size_(KW)'] <= 10:
            df_working.at[index, 'net_estimated_cost'] = (15*row['system_output_annual']/1000) * (78.51 + 82.22)/2 # For systems <= 10KW, get paid ~$80 per MWh of production over 15 years
        elif row['state'] == 'IL' and row['recommended_system_size_(KW)'] > 10:
            df_working.at[index, 'net_estimated_cost'] = (15*row['system_output_annual']/1000) * (66.39 + 71.89)/2 # For systems <= 10KW, get paid ~$70 per MWh of production over 15 years

    # --------------------------------------------- ADD NET COST OF BATTERY AFTER BATTERY INCENTIVES ---------------------------------------------

    # Create a new column called 'net_battery_cost' that is the cost of the battery after rebates
    df_working['net_battery_cost'] = 0

    # If state has net metering, then we assume the homeowners get batteries, factoring in a 30% IRA federal rebate
    for index, row in df_working.iterrows():
        if row['net_metering'] == 0:
            df_working.at[index, 'net_battery_cost'] = BATTERY_COST*(1-0.3)

    # Some states have additional rebate programs
    for index, row in df_working.iterrows():
        if row['net_metering'] == 0 and row['state'] == 'CA':
            df_working.at[index, 'net_battery_cost'] = row['net_battery_cost'] - BATTERY_KWH*150
        if row['net_metering'] == 0 and row['state'] == 'HI':
            df_working.at[index, 'net_battery_cost'] = row['net_battery_cost'] - min(BATTERY_KW*850, 5*850) # Note this is for POWER capacity, not energy capacity. 5 kW limit.
        if row['net_metering'] == 0 and row['state'] == 'MD':
            df_working.at[index, 'net_battery_cost'] = row['net_battery_cost'] - min(BATTERY_COST*0.3, 5000) # 30% rebate up to $5,000
        if row['net_metering'] == 0 and row['state'] == 'OR':
            df_working.at[index, 'net_battery_cost'] = row['net_battery_cost'] - min(BATTERY_KWH*300, BATTERY_COST*0.4, 2500) # you will receive an additional incentive equal to $300 per kilowatt hour (kWh) of storage installed. The storage rebate amount cannot exceed 60% of the net cost of the storage system and it cannot go over $2,500. 
        if row['net_metering'] == 0 and row['state'] == 'NV':
            df_working.at[index, 'net_battery_cost'] = row['net_battery_cost'] - min(BATTERY_KWH*95, BATTERY_COST*0.5, 3000)
            
    df_working['net_estimated_cost'] = df_working['net_estimated_cost'] + df_working['net_battery_cost']

    # column that is total battery incentives
    df_working['battery_incentives'] = 0
    for index, row in df_working.iterrows():
        if row['net_metering'] == 0:
            df_working.at[index, 'battery_incentives'] = BATTERY_COST - row['net_battery_cost']

    #move the net_battery_cost column just after estimated_cost
    cols = list(df_working.columns)
    #find which column number is estiamte cost
    col_num = cols.index('estimated_cost')
    cols.insert(col_num+1, cols.pop(cols.index('net_battery_cost')))
    df_working = df_working.loc[:, cols]

    #move the battery_incentives column just before net_battery_cost
    cols = list(df_working.columns)
    #find which column number is estiamte cost
    col_num = cols.index('net_battery_cost')
    cols.insert(col_num, cols.pop(cols.index('battery_incentives')))
    df_working = df_working.loc[:, cols]
    
    df_working.to_csv('1_output.csv', index=False)
    print('MergeIncentivesCalculateGrossSavings: 1_output\n')

def CalculateProductionSavings(): # TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO
    df_working = pd.read_csv('1_output.csv')

    # --------------------------------------------- CALCULATE PRODUCTION SAVINGS: SAVINGS FROM NET METERING & SRECs ---------------------------------------------

    # net metering does not apply to excess production above annual demand. SRECs apply to ALL production
    df_working['eligible_production'] = df_working[['system_output_annual','avg_electricity_use_kwh']].min(axis=1)

    # We multiply by 'electricity_price' even where net metering is 0, bc we assume that they get a battery savings are equivalent to the forgone electricity costs
    # FOR STATES WIHTOUT NET METERING: change to just include first half of this equation, ignore SRECs, bc power not being provided to grid, just straight to battery
    # I CHECKED: in states without net metering, the SREC price is 0
    for index, row in df_working.iterrows():
        if row['net_metering'] == 0:
            # if there is no net metering, then the savings are just the forgone electricity costs
            df_working.at[index, 'year1_production_savings'] = row['eligible_production'] * row['electricity_price']
        else:
            df_working.at[index, 'year1_production_savings'] = row['eligible_production'] * row['electricity_price'] + row['system_output_annual'] * row['SREC_$_kwh']
    
    # Create a new column called '20_year_production_savings' that is the 20 year production savings, taking into account a 2.2% annual increase in electricity prices
    df_working['20_year_production_savings'] = 0
    df_working['TEMP_net_metering_price'] = df_working['electricity_price']
    for index, row in df_working.iterrows():
        year = 1 
        while year <= NET_SAVINGS_YEARS:
            row['20_year_production_savings'] = row['20_year_production_savings'] + row['eligible_production'] * row['TEMP_net_metering_price']
            row['TEMP_net_metering_price'] = row['electricity_price'] * ENERGY_PRICE_GROWTH_RATE**year #Update the price according to the rate of inflation. ** is python for exponent
            year += 1
        if row['net_metering'] == 1: #If state has net metering, add 20 years of SREC revenue
            df_working.loc[index, '20_year_production_savings'] = row['20_year_production_savings'] + NET_SAVINGS_YEARS*row['system_output_annual']*row['SREC_$_kwh']
        if row['net_metering'] == 0:
            df_working.loc[index, '20_year_production_savings'] = row['20_year_production_savings']


    df_working.drop(columns=['TEMP_net_metering_price'], inplace=True)

    df_working.to_csv('1_output.csv', index=False)
    print('CalculateProductionSavings: 1_output\n')

def CalculatePaybackPeriod(): # done
    df_working = pd.read_csv('1_output.csv')

    df_working = df_working.assign(energy_price_growth_rate=ENERGY_PRICE_GROWTH_RATE) #According to the EIA, electricity prices have increased 1.8% per year in the United States for the past 25 years
    #df_working = df_working.assign(cumulative_savings=0)
    df_working['cumulative_savings'] = 0
    df_working = df_working.assign(payback_period=None) 

    df_working['TEMP_net_metering_price'] = df_working['electricity_price'] #Create a temporary column for the output incentive price, which will be updated each year    

    #Looping through each row, find the payback period for the system
    for index, row in df_working.iterrows():
        year = 1
        while row['cumulative_savings'] <= row['net_estimated_cost']:
            row['cumulative_savings'] = row['cumulative_savings'] + row['eligible_production'] * row['TEMP_net_metering_price'] + row['output_annual']*row['SREC_$_kwh']
            row['TEMP_net_metering_price'] = row['electricity_price'] * row['energy_price_growth_rate']**year #For each year, update the price according to the rate of inflation. ** is python for exponent
            year += 1
            if year > 30:
                print('ERROR: Payback period is greater than 30 years.')
                break

        #Update the DataFrame
        df_working.loc[index, 'cumulative_savings'] = row['cumulative_savings']
        df_working.loc[index, 'payback_period'] = year-1
    
    df_working.drop(columns=['TEMP_net_metering_price'], inplace=True)

    df_working.to_csv('1_output.csv', index=False)
    print('CalculatePaybackPeriod: 1_output\n')

def CalculateLoanPayments(): # TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO  TO DO
    df_working = pd.read_csv('1_output.csv')

    if USE_USB_INTEREST_RATES == True: #If using USB interest rates
        df_USB_interest_rates = pd.read_csv('/Users/peterlehner/Dropbox/Climata_GoingSolo/USB_zips.csv')
        df_USB_interest_rates = df_USB_interest_rates[['zip', 'Median_Variable_Rate']]
        df_working = pd.merge(df_working, df_USB_interest_rates, left_on='zip', right_on='zip', how='left')
        df_working['Median_Variable_Rate'] = df_working['Median_Variable_Rate'].astype(float)

    # TEMP_CODE
    #df_working['net_estimated_cost'] = df_working['net_estimated_cost'] + df_working['federal_incentive']

    if USE_USB_INTEREST_RATES == True: #If using USB interest rates
        df_working['monthly_interest_payment'] = (df_working['net_estimated_cost'] * (df_working['Median_Variable_Rate']/12)) / (1 - (1 + (df_working['Median_Variable_Rate']/12))**(-12*DEFAULT_LOAN_TERM))
    else:
        df_working['monthly_interest_payment'] = (df_working['net_estimated_cost'] * (DEFAULT_INTEREST_RATE/12)) / (1 - (1 + (DEFAULT_INTEREST_RATE/12))**(-12*DEFAULT_LOAN_TERM))
    df_working['yearly_interest_payment'] = df_working['monthly_interest_payment']*12
    df_working['year1_net_savings'] = df_working['year1_production_savings'] - df_working['yearly_interest_payment']
    df_working['20yr_net_savings'] = df_working['20_year_production_savings'] - df_working['yearly_interest_payment']*NET_SAVINGS_YEARS

    # calculate the breakeven interest rate percent for each row
    df_working = df_working.assign(TEMP_yearly_interest_payment=999999)
    df_working = df_working.assign(breakeven_interest_rate=None)
    index = 0
    for index, row in df_working.iterrows():
        breakeven_interest_rate = 0.3
        while row['TEMP_yearly_interest_payment'] > row['year1_production_savings']:
            #For each interest rate, calculate yearly payments
            row['TEMP_yearly_interest_payment'] = 12*((row['net_estimated_cost'] * (breakeven_interest_rate/12)) / (1 - (1 + (breakeven_interest_rate/12))**(-12*DEFAULT_LOAN_TERM)))
            breakeven_interest_rate = breakeven_interest_rate - 0.001 #Incrementally lower the breakeven interest rate
            breakeven_interest_rate = round(breakeven_interest_rate, 3)
            if breakeven_interest_rate < 0.000001: #If interest rate reaches 0 before breakeven, then break while loop
                breakeven_interest_rate = None
                break

        #Update the DataFrame
        df_working.loc[index, 'breakeven_interest_rate'] = breakeven_interest_rate

    df_working.drop(columns=['TEMP_yearly_interest_payment'], inplace=True)

    df_working.to_csv('1_output.csv', index=False)
    print('CalculateLoanPayments: 1_output\n')

def BuildInterestRateSensitivityTable():# done
    df_working = pd.read_csv('1_output.csv')

    for r in np.arange(0.01, 0.16, 0.01):
        r = round(r, 2)

        df_working[str(r) + '_net_yearly_savings'] = df_working['year1_production_savings'] - 12*(df_working['net_estimated_cost'] * (r/12)) / (1 - (1 + (r/12))**(-12*DEFAULT_LOAN_TERM))
        df_working[str(r) + '_net_yearly_savings'] = df_working[str(r) + '_net_yearly_savings'].round()

    #write data to a new csv file
    df_working.to_csv('1_output.csv', index=False)
    print('BuildInterestRateSensitivityTable: 1_output\n')

def ClearHPdatafromSolar():# done
    df_working = pd.read_csv('1_output.csv')

    if net_of_heatpumps == False:
        # Overwrite all values in the above columns to be None
        df_working.loc[:, "status_quo_electricity"] = None
        df_working.loc[:, "status_quo_natgas"] = None
        df_working.loc[:, "heatpump_electricity"] = None
        df_working.loc[:, "natgas_price_$_per_1000_cf_2021"] = None
        df_working.loc[:, "cost_before_heatpump"] = None
        df_working.loc[:, "cost_after_heatpump"] = None
        df_working.loc[:, "heatpump_savings"] = None

    df_working.to_csv('1_output.csv', index=False)

def RoundFields(): # done
    df_working = pd.read_csv('1_output.csv')

    df_working['capacity_factor']              = df_working['capacity_factor'].round(3)
    df_working['avg_electricity_use_kwh']      = df_working['avg_electricity_use_kwh'].round()
    df_working['avg_electric_bill_monthly']    = df_working['avg_electric_bill_monthly'].round()
    df_working['recommended_system_size_(KW)'] = df_working['recommended_system_size_(KW)'].round(1)
    df_working['electricity_price']            = df_working['electricity_price'].round(3)
    df_working['estimated_cost']               = df_working['estimated_cost'].round()
    df_working['federal_incentive']            = df_working['federal_incentive'].round()
    df_working['state_incentive_by_percent']   = df_working['state_incentive_by_percent'].round()
    df_working['net_estimated_cost']           = df_working['net_estimated_cost'].round()
    df_working['year1_production_savings']     = df_working['year1_production_savings'].round()
    df_working['cumulative_savings']           = df_working['cumulative_savings'].round()
    df_working['state_incentive_by_W']         = df_working['state_incentive_by_W'].round()
    df_working['monthly_interest_payment']     = df_working['monthly_interest_payment'].round()
    df_working['yearly_interest_payment']      = df_working['yearly_interest_payment'].round()
    df_working['year1_net_savings']            = df_working['year1_net_savings'].round()
    df_working['system_output_annual']         = df_working['system_output_annual'].round()
    df_working['eligible_production']          = df_working['eligible_production'].round()
    df_working['cost_before_heatpump']         = df_working['cost_before_heatpump'].round()
    df_working['cost_after_heatpump']          = df_working['cost_after_heatpump'].round()
    df_working['heatpump_savings']             = df_working['heatpump_savings'].round()

    df_working.to_csv('1_output.csv', index=False)

def DropFields(): # done
    df_working = pd.read_csv('1_output.csv')

    df_working.drop(columns=['output_annual',
    'sizing_ratio',
    'natgas_price_$_per_1000_cf_2021',
    'avg_cost_per_kw',
    'W_incentive_max_$',
    'incentive_per_W',
    'percent_incentive_max_$',
    'incentive_percent',
    'eligible_production',
    'cumulative_savings'], inplace=True)

    # Drop all the interest rate sensitivity columns
    for r in np.arange(0.01, 0.16, 0.01):
        r = round(r, 2)
        df_working.drop(columns=[str(r) + '_net_yearly_savings'], inplace=True)

    df_working.to_csv('1_output.csv', index=False)

def RenameFields(): # done
    df_working = pd.read_csv('1_output.csv')

    for column in df_working.columns:
        df_working.rename(columns={column:column.capitalize().replace("_"," ")},inplace=True)

    # raname column 'average energy use (kwh)' to 'average energy use (kwh, yearly)'
    df_working.rename(columns={'Average energy use (kwh)':'Average energy use (kwh, yearly)'},inplace=True)
    df_working.rename(columns={'Price':'Price ($)'},inplace=True)
    df_working.rename(columns={'Cost before heatpump':'Utilities before heatpump ($, yearly)'},inplace=True)
    df_working.rename(columns={'Cost after heatpump':'Utilities after heatpump ($, yearly)'},inplace=True)
    df_working.rename(columns={'Heatpump savings':'Heatpump savings ($, yearly)'},inplace=True)
    df_working.rename(columns={'Estimated cost':'Estimated system cost ($)'},inplace=True)
    df_working.rename(columns={'Srec $ kwh':'Srec ($ per kwh)'},inplace=True)
    df_working.rename(columns={'Net metering':'Net metering flag'},inplace=True)
    df_working.rename(columns={'Federal incentive':'Federal tax incentive ($)'},inplace=True)
    df_working.rename(columns={'State incentive by percent':'State tax incentive ($)'},inplace=True)
    df_working.rename(columns={'State incentive by w':'State watt incentive ($)'},inplace=True)
    df_working.rename(columns={'Net estimated cost':'Net estimated cost ($)'},inplace=True)
    df_working.rename(columns={'System output annual':'System output annual (kwh)'},inplace=True)
    df_working.rename(columns={'Year1 production savings':'Year 1 production savings ($)'},inplace=True)
    df_working.rename(columns={'Monthly interest payment':'Monthly interest payment ($)'},inplace=True)
    df_working.rename(columns={'Yearly interest payment':'Yearly interest payment ($)'},inplace=True)
    df_working.rename(columns={'Net yearly savings':'Net yearly savings ($)'},inplace=True)
    df_working.rename(columns={'0.01 net yearly savings':'0.01 net yearly savings ($)'},inplace=True)
    df_working.rename(columns={'0.02 net yearly savings':'0.02 net yearly savings ($)'},inplace=True)
    df_working.rename(columns={'0.03 net yearly savings':'0.03 net yearly savings ($)'},inplace=True)
    df_working.rename(columns={'0.04 net yearly savings':'0.04 net yearly savings ($)'},inplace=True)
    df_working.rename(columns={'0.05 net yearly savings':'0.05 net yearly savings ($)'},inplace=True)
    df_working.rename(columns={'0.06 net yearly savings':'0.06 net yearly savings ($)'},inplace=True)
    df_working.rename(columns={'0.07 net yearly savings':'0.07 net yearly savings ($)'},inplace=True)
    df_working.rename(columns={'0.08 net yearly savings':'0.08 net yearly savings ($)'},inplace=True)
    df_working.rename(columns={'0.09 net yearly savings':'0.09 net yearly savings ($)'},inplace=True)
    df_working.rename(columns={'0.1 net yearly savings':'0.10 net yearly savings ($)'},inplace=True)
    df_working.rename(columns={'0.11 net yearly savings':'0.11 net yearly savings ($)'},inplace=True)
    df_working.rename(columns={'0.12 net yearly savings':'0.12 net yearly savings ($)'},inplace=True)
    df_working.rename(columns={'0.13 net yearly savings':'0.13 net yearly savings ($)'},inplace=True)
    df_working.rename(columns={'0.14 net yearly savings':'0.14 net yearly savings ($)'},inplace=True)
    df_working.rename(columns={'0.15 net yearly savings':'0.15 net yearly savings ($)'},inplace=True)

    df_working.to_csv('1_output.csv', index=False)

def OutputSeperateFiles(): # done
    df_working = pd.read_csv('1_output.csv')

    if net_of_heatpumps == False:
        df_working.to_csv('Final_output_solar.csv', index=False)
    else:
        df_working.to_csv('Final_output_solarheatpump.csv', index=False)

    print('OutputSeperateFiles: Final_output csvs\n')

def CombineFiles(): # done
    df_solar_only = pd.read_csv('Final_output_solar.csv')
    df_solar_heatpump = pd.read_csv('Final_output_solarheatpump.csv')

    # # For the initial runs that we send to banks, exclude zip codes that don't have heatpump data
    # zip_codes_to_exclude = df_solar_heatpump[df_solar_heatpump['Utilities before heatpump ($, yearly)'].isnull()]['zip']
    # df_solar_only = df_solar_only[~df_solar_only['Zip code'].isin(zip_codes_to_exclude)]
    # df_solar_heatpump = df_solar_heatpump[~df_solar_heatpump['Zip code'].isin(zip_codes_to_exclude)]

    writer = pd.ExcelWriter('Final_output_combined.xlsx', engine='xlsxwriter')

    df_solar_only.to_excel(writer, sheet_name='Solar only',index=False)
    df_solar_heatpump.to_excel(writer, sheet_name='Solar & heat pump',index=False)

    writer.close()
    print('CombineFiles: Final_output_combined.xlsx\n')

def pretty_print_response(response): #turn on as needed when testing the API 
    #Create Python object from JSON string data, the pretty print json
    response_json = response.text
    obj = json.loads(response_json)
    json_formatted_str = json.dumps(obj, indent=4)
    print(json_formatted_str)

#Some NREL PVWatts API parameters
SYSTEM_CAPACITY = 1 #Nameplate capacity (kW). Nameplate Capacity (kW) = (Percent of Building Load * Annual Building Load (kWh)) / (8760 * Capacity Factor ).
DIRECTIONS_IN = [180] #For each zip code, we get the solar output for roofs facing 135 and 225 degrees. See PVwatts documentation.xlsx for explanation.
SOILING = 1.13 #This is a percent reduction. See "Assumptions_SOILING.xlsx" for reasoning behind this number

#Key assumptions for calculating savings net of loan payments
ENERGY_PRICE_GROWTH_RATE = 1.022
DEFAULT_INTEREST_RATE = 0.06
#DEFAULT_INTEREST_RATE = 0.09 # TEMP_CODE for SpringEQ
DEFAULT_LOAN_TERM = 20

BATTERY_COUNT = 1
BATTERY_COST  = 14200 # Tesla Powerwall
BATTERY_KWH   = 13.5 # Tesla Powerwall capacity
BATTERY_KW    = 5 # Tesla Powerwall real power, KW, max continuous (charge and discharge)
BATTERY_COST  = BATTERY_COST * BATTERY_COUNT
BATTERY_KWH   = BATTERY_KWH * BATTERY_COUNT
BATTERY_KW    = BATTERY_KW * BATTERY_COUNT

NET_SAVINGS_YEARS = DEFAULT_LOAN_TERM #THIS HAS TO STAY. Otherwise net savings calc breaks

#All 50 states and DC
ALL_STATES = ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY']
APPLICAPLE_STATES = ALL_STATES

USE_USB_INTEREST_RATES = False

HAVE_CACHED_NREL_OUTPUT = True
HAVE_CACHED_KELVIN_OUTPUT = True
RUNTIME_DELAY = False # TURN THIS ON IF RUNNING MORE  THAN 1000 zips per hour

TAKE_SAMPLE = True
NUMBER_OF_ZIPS = 3

if __name__ == "__main__":
    t0 = time.time()

    #This section pulls data that does not differ whether someone has a heat pump or not:

    SelectZipCodes()

    if HAVE_CACHED_NREL_OUTPUT == False:
        CallSolarAPI()
    else:
        MergeCachedNRELoutput()
    
    MergeZipLevelDemand()
    CalculateSizingRatio()
    
    if HAVE_CACHED_KELVIN_OUTPUT == False:
        CallHeatPumpAPI()
    else:
        MergeCachedKelvinOutput()

    for i in range(0, 2): #comment out this line if you want to only run solar
    #for i in range(0, 1): #use this line if you just want to run solar only or heat pumps only

        net_of_heatpumps = False if i == 0 else True
        #net_of_heatpumps = False #use this line if you just want to run solar only or heat pumps only
        print(f'HEAT PUMP: {net_of_heatpumps}\n')

        CalculateRecommendedSystemSize()
        MergeCosts()
        MergeIncentivesCalculateGrossSavings()
        CalculateProductionSavings()
        CalculatePaybackPeriod()
        CalculateLoanPayments()
        BuildInterestRateSensitivityTable()

        # Output prepartion for each file:

        ClearHPdatafromSolar()
        RoundFields() 
        DropFields()
        RenameFields()
        OutputSeperateFiles()
        
    CombineFiles()

    print(f'\nExecution time (s): {round(time.time() - t0)}')