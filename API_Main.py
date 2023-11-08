import pandas as pd
import requests
import numpy as np
import json
import time
from Heatpumps import CallHeatPumpAPI

def SelectZipCodes(zip_query):
    INPUT_DF = pd.read_csv('/Users/peterlehner/Dropbox/Climata/Data/Zips/zip_lat_lon_state.csv')

    #I was lazy and just hardcoded this list from the state_to_DSIRE_incentives_122822 file
    #states_with_net_metering = ['MA', 'DC', 'RI', 'CA', 'NY', 'NJ', 'WA', 'OR', 'CT', 'NM', 'UT', 'CO', 'FL', 'MD', 'TX', 'ME', 'MN', 'VT', 'IL', 'NH', 'OH', 'PA', 'IA', 'ID', 'VA', 'NC', 'AK', 'AR', 'WV', 'DE', 'MT', 'KS']
    #INPUT_DF = INPUT_DF[INPUT_DF['state'].isin(states_with_net_metering)] # Only keep zips in states relevant to the selected bank

    #INPUT_DF = INPUT_DF[INPUT_DF['state'].isin(APPLICAPLE_STATES)] # Only keep zips in states relevant to the selected bank
    INPUT_DF['zip_code'] = [str(x).zfill(5) for x in INPUT_DF['zip_code']] # Make all zips string and 5 characters

    zip_query_row = INPUT_DF.loc[INPUT_DF['zip_code'] == zip_query] 

    zip_query_row.to_csv('0_zips_to_run.csv', index=False)
    print('\nSelectZipCodes()\n')

def CallSolarAPI():
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
    
    for l in range(len(df_pvwatts_input)):
        zip_code = df_pvwatts_input.at[l,'zip_code']
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
        response = requests.request("GET", URL, params = parameters)
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
        
        print(f'Zip code:        {zip_code}')              
        print(f'Calls remaining: {calls_remaining}\n')
        
        if int(calls_remaining) < 100: #NREL rate limits the API to 1000 calls / hour. Refreshes on a rolling basis. 
            print("Sleeping...")
            time.sleep(36)

    #create dataframe from lists
    data = {'zip_code':zip_codes_out,
         'lat': latitudes,
         'lon': longitudes,
         'state': states,
         'output_annual': output_annuals}
    df_working = pd.DataFrame(data)
    
    df_working.to_csv('0_output.csv', index=False)
    print('CallSolarAPI()\n')

def MergeZipLevelDemand(electric_bill_query):
    df_working = pd.read_csv('0_output.csv')
    df_working['zip_code'] = df_working['zip_code'].apply(str).str.zfill(5)

    #Read in zip level demand data
    df_prices = pd.read_csv('/Users/peterlehner/Dropbox/Climata/Data/Energy/zip_to_avg_energy_bill.csv')
    
    #clean up zip codes amd rename column
    df_prices['zip'] = df_prices['zip'].apply(str).str.zfill(5)
    df_prices = df_prices.rename(columns = {'zip':'zip_code'})

    #merge dataframes. This merge adds columns: Average energy use (kWh) and Average Electricity Bill (USD)
    df_working = pd.merge(df_working, df_prices, left_on='zip_code', right_on='zip_code', how='left')
    df_working.drop(columns=['Random #'], inplace=True)
    df_working = df_working.rename(columns={'Average energy use (kWh)':'Average_energy_use_(kWh)'})
    
    #calculate recommended system size in nameplace KW capacity
    #df_working['recommended_system_size_(KW)'] = df_working['Average_energy_use_(kWh)']*df_working['sizing_ratio'] # e.g.: 10,000 KWH * (1 KW / 1000 KWH) = 10 KW.   10 KW * (1000 KWH / 1 KW) = 10,000 KWH

    df_working['Average_energy_use_(kWh)'] = df_working['Average_energy_use_(kWh)'].astype(float)
    df_working['Average electric bill ($, monthly)'] = df_working['Average electric bill ($, monthly)'].astype(float)
    
    #calculate the price of energy in $/kWh for that zip code
    df_working['price'] = (12*df_working["Average electric bill ($, monthly)"])/df_working['Average_energy_use_(kWh)']

    #NEW CODE FOR API - Want to allow for the user to input their own electric bill
    df_working['Average_energy_use_(kWh)'] = (12*electric_bill_query)/df_working['price']

    df_working.to_csv('0_output.csv', index=False)
    print('MergeZipLevelDemand()\n')


def CalculateSizingRatio():    
    df_working = pd.read_csv('0_output.csv')

    df_working['capacity_factor'] = df_working['output_annual']/8760
    df_working['sizing_ratio'] = 1/df_working['output_annual']
    df_working.to_csv('0_output.csv', index=False)
    print('CalculateSizingRatio()\n')

# Call heat pump API

def CalculateRecommendedSystemSize():
    df_working = pd.read_csv('0_output.csv')

    if net_of_heatpumps == True:
        df_working['Average_energy_use_(kWh)'] = df_working['Average_energy_use_(kWh)'] + df_working["heatpump_electricity"]
        df_working['Heat pump'] = 'Yes'
        df_working['Average electric bill ($, monthly)'] = df_working['Average_energy_use_(kWh)']*df_working['price']/12
    else:
        df_working['Heat pump'] = 'No'

    df_working['recommended_system_size_(KW)'] = df_working['Average_energy_use_(kWh)']*df_working['sizing_ratio'] # e.g.: 10,000 KWH * (1 KW / 1000 KWH) = 10 KW.   10 KW * (1000 KWH / 1 KW) = 10,000 KWH

    #take the mininum of the recommended system size and 15 KW because roofs can't fit large arrays
    df_working['recommended_system_size_(KW)'] = df_working['recommended_system_size_(KW)'].apply(lambda x: min(x, 15))

    df_working.to_csv('1_output.csv', index=False)
    print('CalculateRecommendedSystemSize()\n')

def MergeCosts():
    df_working = pd.read_csv('1_output.csv')

    #This file adds a column with the average price per KW for each state
    df_costs = pd.read_csv('/Users/peterlehner/Dropbox/Climata/Data/Cost/state_to_cost_per_kw.csv', usecols=['state','avg_cost_per_kw'])

    df_working = pd.merge(df_working, df_costs, on='state', how='left')

    df_working['estimated_cost'] = df_working['avg_cost_per_kw']*df_working['recommended_system_size_(KW)']

    df_working.to_csv('1_output.csv', index=False)
    print('MergeCosts()\n')

def MergeIncentivesCalculateGrossSavings():
    df_working = pd.read_csv('1_output.csv')

    #This file adds columns: state_name, climata_rank, percent_incentive_max_$, incentive_percent, net_of_federal, SREC_$_kwh, and net_metering
    df_incentives = pd.read_csv('/Users/peterlehner/Dropbox/Climata/Data/Incentives/state_to_DSIRE_incentives_122822.csv')
    df_incentives.drop(columns=['state_name', 'climata_rank'], inplace=True)

    df_working = pd.merge(df_working, df_incentives, on='state', how='left') 

    # --------------------------------------------- CALCULATE TAX REBATES AND INCENTIVES ---------------------------------------------
    
    # FEDERAL
    df_working['federal_incentive'] = 0.3*df_working['estimated_cost']

    # STATE
    #create a temporary column for the cost of the system NET of the federal tax credit (for applicable states, of course)
    for index, row in df_working.iterrows():
        #print(f'\nindex: {index}, row: {row}\n')
        if row['net_of_federal'] == 1:
            df_working.loc[index, 'temp_cost'] = row['estimated_cost']*.7
        else:
            df_working['temp_cost'] = df_working['estimated_cost']
    
    #Calculate state incentive
    #First, calculate state incentive by percent of system cost
    for index, row in df_working.iterrows():
        if row['incentive_percent'] == 0:
            df_working.loc[index, 'state_incentive_by_percent'] = row['percent_incentive_max_$']
        elif row['percent_incentive_max_$'] == 0:
            row['incentive_percent']= row['incentive_percent'].astype(float)
            row['temp_cost'] = row['temp_cost'].asytpe(float)
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
    df_working['total_upfront_incentives'] = df_working['federal_incentive'] + df_working['state_incentive_by_percent'] + df_working['state_incentive_by_W']

    df_working.drop(columns=['temp_cost'], inplace=True)
    
    # --------------------------------------------- CALCULATE SAVINGS FROM NET METERING & SRECs ---------------------------------------------

    #FILTER OUT WHERE NET METERING = 0. CONFIRM WITH RORY THAT WE SHOULD DO THIS

    #remove rows where net metering is 0
    df_working = df_working[df_working['net_metering'] != 0]

    #Since 'net_metering' from the incentive file is a 0 or 1 binary tag, simply multiply this by the price for that row to get the net metering price
    df_working['net_metering_price'] = df_working['net_metering']*df_working['price']

    if any(df_working['net_metering_price']) > 1: #Just a sanity check
        print('\n!!!!!!!! ERROR: Net metering is greater than $0.50/kwh.')
        exit()

    # net metering does not apply to excess production above annual demand. SRECs apply to ALL production
    df_working['system_output_annual'] = df_working['recommended_system_size_(KW)']*df_working['output_annual']
    df_working['eligible_production'] = df_working[['system_output_annual','Average_energy_use_(kWh)']].min(axis=1)
    df_working['year1_production_savings'] = df_working['eligible_production'] * df_working['net_metering_price'] + df_working['output_annual']*df_working['SREC_$_kwh']
    
    df_working.to_csv('1_output.csv', index=False)
    print('MergeIncentivesCalculateGrossSavings()\n')

def CalculateNetSavings():
    df_working = pd.read_csv('1_output.csv')

    df_working = df_working.assign(energy_price_growth_rate=ENERGY_PRICE_GROWTH_RATE) #According to the EIA, electricity prices have increased 1.8% per year in the United States for the past 25 years
    df_working = df_working.assign(cumulative_savings=0)
    df_working = df_working.assign(payback_period=None) 

    #Create a temporary column for the output incentive price, which will be updated each year    
    df_working['TEMP_net_metering_price'] = df_working['net_metering_price']

    #Looping through each row, find the payback period for the system
    for index, row in df_working.iterrows():
        year = 1
        while row['cumulative_savings'] <= row['net_estimated_cost']:

            #For each year, add to the cumulative savings the output for that year (temp output) multiplied by the price for that year (temp price).
            row['cumulative_savings'] = row['cumulative_savings'] + row['eligible_production'] * row['TEMP_net_metering_price'] + row['output_annual']*row['SREC_$_kwh']

            #For each year, update the price according to the rate of inflation. ** is python for exponent
            row['TEMP_net_metering_price'] = row['net_metering_price'] * row['energy_price_growth_rate']**year

            year += 1

        #Update the DataFrame
        df_working.loc[index, 'cumulative_savings'] = row['cumulative_savings']
        df_working.loc[index, 'payback_period'] = year-1
    
    df_working.drop(columns=['TEMP_net_metering_price'], inplace=True)

    df_working.to_csv('1_output.csv', index=False)
    print('CalculateNetSavings()\n')

def CalculateLoanPayments():
    df_working = pd.read_csv('1_output.csv')

    df_working['monthly_interest_payment'] = (df_working['net_estimated_cost'] * (DEFAULT_INTEREST_RATE/12)) / (1 - (1 + (DEFAULT_INTEREST_RATE/12))**(-12*DEFAULT_LOAN_TERM))

    df_working['yearly_interest_payment'] = df_working['monthly_interest_payment']*12

    df_working['net_yearly_savings'] = df_working['year1_production_savings'] - df_working['yearly_interest_payment']

    # calculate the breakeven interest rate percent for each row
    df_working = df_working.assign(TEMP_yearly_interest_payment=999999)
    df_working = df_working.assign(breakeven_interest_rate=None)
    index = 0
    for index, row in df_working.iterrows():
        breakeven_interest_rate = 0.5
        while row['TEMP_yearly_interest_payment'] > row['year1_production_savings']:
            #For each interest rate, calculate yearly payments
            row['TEMP_yearly_interest_payment'] = 12*((row['net_estimated_cost'] * (breakeven_interest_rate/12)) / (1 - (1 + (breakeven_interest_rate/12))**(-12*DEFAULT_LOAN_TERM)))

            #Incrementally lower the breakeven interest rate
            breakeven_interest_rate = breakeven_interest_rate - 0.001
            breakeven_interest_rate = round(breakeven_interest_rate, 3)
            
            if breakeven_interest_rate < 0.000001: #If interest rate is 0, then break
                breakeven_interest_rate = None
                break

        #Update the DataFrame
        df_working.loc[index, 'breakeven_interest_rate'] = breakeven_interest_rate

    df_working.drop(columns=['TEMP_yearly_interest_payment'], inplace=True)

    df_working.to_csv('1_output.csv', index=False)
    print('CalculateLoanPayments()\n')

def BuildInterestRateSensitivityTable():
    df_working = pd.read_csv('1_output.csv')

    for r in np.arange(0.01, 0.16, 0.01):
        r = round(r, 2)

        df_working[str(r) + '_net_yearly_savings'] = df_working['year1_production_savings'] - 12*(df_working['net_estimated_cost'] * (r/12)) / (1 - (1 + (r/12))**(-12*DEFAULT_LOAN_TERM))
        df_working[str(r) + '_net_yearly_savings'] = df_working[str(r) + '_net_yearly_savings'].round()

    #write data to a new csv file
    df_working.to_csv('1_output.csv', index=False)
    print('BuildInterestRateSensitivityTable()\n')

def PrepareOutput():
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

    df_working['capacity_factor']                    = df_working['capacity_factor'].round(3)
    df_working['Average_energy_use_(kWh)']           = df_working['Average_energy_use_(kWh)'].round()
    df_working['Average electric bill ($, monthly)'] = df_working['Average electric bill ($, monthly)'].round()
    df_working['recommended_system_size_(KW)']       = df_working['recommended_system_size_(KW)'].round(1)
    df_working['price']                              = df_working['price'].round(3)
    df_working['estimated_cost']                     = df_working['estimated_cost'].round()
    df_working['federal_incentive']                  = df_working['federal_incentive'].round()
    df_working['state_incentive_by_percent']         = df_working['state_incentive_by_percent'].round()
    df_working['net_estimated_cost']                 = df_working['net_estimated_cost'].round()
    df_working['net_metering_price']                 = df_working['net_metering_price'].round(3)
    df_working['year1_production_savings']           = df_working['year1_production_savings'].round()
    df_working['cumulative_savings']                 = df_working['cumulative_savings'].round()
    df_working['state_incentive_by_W']               = df_working['state_incentive_by_W'].round()
    df_working['monthly_interest_payment']           = df_working['monthly_interest_payment'].round()
    df_working['yearly_interest_payment']            = df_working['yearly_interest_payment'].round()
    df_working['net_yearly_savings']                 = df_working['net_yearly_savings'].round()
    df_working['system_output_annual']               = df_working['system_output_annual'].round()
    df_working['eligible_production']                = df_working['eligible_production'].round()
    if net_of_heatpumps == True:
        df_working['cost_before_heatpump']               = df_working['cost_before_heatpump'].round()
        df_working['cost_after_heatpump']                = df_working['cost_after_heatpump'].round()
        df_working['heatpump_savings']                   = df_working['heatpump_savings'].round()

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

    return df_working

#Some NREL PVWatts API parameters
SYSTEM_CAPACITY = 1 #Nameplate capacity (kW). Nameplate Capacity (kW) = (Percent of Building Load * Annual Building Load (kWh)) / (8760 * Capacity Factor ).
DIRECTIONS_IN = [180] #For each zip code, we get the solar output for roofs facing 135 and 225 degrees. See PVwatts documentation.xlsx for explanation. 
SOILING = 1.13 #This is a percent reduction. See "Assumptions_SOILING.xlsx" for reasoning behind this number

#Key assumptions for calculating savings net of loan payments
ENERGY_PRICE_GROWTH_RATE = 1.018
DEFAULT_INTEREST_RATE = 0.06
DEFAULT_LOAN_TERM = 20

#As determined by Rory, we will filter to these states and ignore all other zip codes
APPLICAPLE_STATES = ['CA', 'MA', 'NY', 'NJ', 'WA', 'OR', 'CT', 'NM', 'UT', 'AZ', 'CO', 'FL', 'MD', 'TX', 'ME', 'DC', 'MN', 'HI', 'NV', 'VT', 'RI', 'IL', 'WI', 'NH',"OH", "PA", "IA", "ID", "IN", "VA", "NC", "AK", "AR", "WV"]

def main(zip_query, heatpump_query, electric_bill_query):
    t0 = time.time()

    global net_of_heatpumps

    t1 = time.time()

    #this section pulls data that does not differ whether someone has a heat pump or not
    SelectZipCodes(zip_query)

    t2 = time.time()

    CallSolarAPI()

    t3 = time.time()

    MergeZipLevelDemand(electric_bill_query)
    CalculateSizingRatio()

    net_of_heatpumps = heatpump_query

    if heatpump_query == True:
        CallHeatPumpAPI() # Function defined in "heatpumps.py" 

    CalculateRecommendedSystemSize()
    MergeCosts()
    MergeIncentivesCalculateGrossSavings()
    CalculateNetSavings()
    CalculateLoanPayments()
    BuildInterestRateSensitivityTable()
    df_final = PrepareOutput() # Out: Final_output_combined.xlsx

    net_savings_for_API = df_final['Net yearly savings ($)'].sum()
    heatpump_savings = df_final['Heatpump savings ($, yearly)'].sum()
    total_upfront_incentives = round(df_final['Total upfront incentives'].sum(),0)

    print('net_savings_for_API: ', net_savings_for_API)
    print('heatpump_savings: ', heatpump_savings)
    print('total_upfront_incentives: ', total_upfront_incentives)

    t99 = time.time()

    before_API = round(t2-t0,2)
    API_run = round(t3-t2,2)
    after_API = round(t99-t3,2)

    total_time = round(t99-t0,2)

    print('\n')
    print('Time to run everything before API: ', before_API)
    print('Time to run API: ', API_run)
    print('Time to run everything after API: ', after_API)
    print('Total time: ', total_time)

    return net_savings_for_API, heatpump_savings, total_upfront_incentives