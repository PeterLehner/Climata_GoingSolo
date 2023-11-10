import pandas as pd
import requests
import numpy as np
import json
import time
from Heatpumps import CallHeatPumpAPI
from MergeCachedKelvinOutput import MergeCachedKelvinOutput

def PullFromDBmain(zip_query): 
    zip_query = [int(zip_query)] #make zip_query a number. Sometimes it comes in as a string, or has a leading zero
    df_working = pd.read_csv('/Users/peterlehner/Dropbox/Climata_GoingSolo/Data/database_main.csv')
    df_working = df_working[df_working['zip'].isin(zip_query)] #Only keep the rows where the zip code is in the list of zip codes

    dict_working = df_working.to_dict(orient='records')[0] # Convert the one-row DataFrame to a dictionary

    return(dict_working)

def AdjustElectricityUse(dict_working, electric_bill_query):        
    #Calcuate a homeowners electric use based on their electric bill. Else, use the average electric use for the zip code
    if electric_bill_query is not None:
        dict_working['electricity_use_kwh'] = (12*electric_bill_query)/dict_working['electricity_price']
    else:
        dict_working['electricity_use_kwh'] = dict_working['avg_electricity_use_kwh']

    return(dict_working)

def GetHeatpumpSavings(dict_working, sqft_query):
    if sqft_query is not None:
        print("TO DO")
        #CallKelvinAPI(dict_working, sqft_query) ---------------------- TO DO
        # If a sqft is passed into API, call the Kelvin model
    else: #just use the Kelvin results for the average sqft for the zip code
        dict_working['cost_before_heatpump'] = dict_working['avg_cost_before_heatpump']
        dict_working['cost_after_heatpump'] = dict_working['avg_cost_after_heatpump']
        dict_working['heatpump_savings'] = dict_working['avg_heatpump_savings']

    return(dict_working)

# Things deviate based on whether they are get a heat pump
def CalculateRecommendedSystemSize(dict_working, heatpump_query, BATTERY_COUNT, BATTERY_KWH): 
    if heatpump_query == True:
        dict_working['electricity_use_kwh'] = dict_working['electricity_use_kwh'] + dict_working["heatpump_electricity"]
        dict_working['Heat pump'] = 'Yes'
        dict_working['avg_electric_bill_monthly'] = dict_working['electricity_use_kwh']*dict_working['electricity_price']/12
    else:
        dict_working['Heat pump'] = 'No'

    # THIS IS WHERE THINGS DEVIATE BASED ON WHETHER THE STATE HAS NET METERING OR NOT
    
    if dict_working['net_metering'] == 1: #If the state has net metering...
        dict_working['recommended_system_size_(KW)'] = dict_working['electricity_use_kwh'] * dict_working['sizing_ratio'] # e.g.: ~10,000 KWH * (1 KW / ~1000 KWH) = ~10 KW
    else: # If the state doesn't have net metering, calculate how much to scale down the size of the solar array IF the system is paired with a battery (in the case of NO net metering)   
        dict_working['EnergyUse_to_BatterySize'] = dict_working['electricity_use_kwh'] / (BATTERY_COUNT * BATTERY_KWH * 1000)
        dict_working['solarWbattery_system_scaling_factor'] = -0.2017 * dict_working['EnergyUse_to_BatterySize'] + 0.8646  # This linear equation from Battery_sensitivity_analysis.xlsx
        dict_working['recommended_system_size_(KW)'] = dict_working['solarWbattery_system_scaling_factor'] * dict_working['electricity_use_kwh'] * dict_working['sizing_ratio']

    dict_working['recommended_system_size_(KW)'] = min(dict_working['recommended_system_size_(KW)'],15) #take the mininum of the recommended system size and 15 KW because roofs can't fit large arrays

    dict_working['system_output_annual'] = dict_working['recommended_system_size_(KW)']*dict_working['output_annual']

    return(dict_working)

def MergeCosts(dict_working): 
    dict_working['estimated_cost'] = dict_working['avg_cost_per_kw']*dict_working['recommended_system_size_(KW)']
    return(dict_working)

def CalculateSolarIncentives(dict_working): 
    
    #FEDERAL: Tax credit is 30% of system cost
    dict_working['federal_incentive'] = 0.3*dict_working['estimated_cost']

    #create a temporary column for the cost of the system NET of the federal tax credit (for applicable states, of course)
    dict_working['temp_cost'] = dict_working['estimated_cost']*0.7 if dict_working['net_of_federal'] == 1 else dict_working['estimated_cost']
    
    #STATE: Incentive by watt of installed capacity
    amount_flt = dict_working['incentive_per_W']*(1000*dict_working['recommended_system_size_(KW)'])
    amount_max = dict_working['W_incentive_max_USD']
    amount_max = float('inf') if amount_max == 0 else amount_max #if amount_max is 0, then set it to infinity so that it is not the min
    dict_working['state_incentive_by_W'] = min([amount_flt, amount_max]) #if there is no incentive per W, then just take the lump sum in the max column

    #STATE: Incentive by percent of system cost
    amount_flt = dict_working['incentive_percent']*dict_working['temp_cost'] #if there is no max, just take the incentive percent multiplied by the system cost
    amount_max = dict_working['percent_incentive_max_USD']
    amount_max = float('inf') if amount_max == 0 else amount_max #if amount_max is 0, then set it to infinity so that it is not the min
    dict_working['state_incentive_by_percent'] = min([amount_flt, amount_max]) #if there is no incentive percent, then just take the lump sum in the max column

    #Subtract incentives from system cost to get net cost
    dict_working['net_estimated_cost'] = dict_working['estimated_cost'] - dict_working['federal_incentive'] - dict_working['state_incentive_by_percent'] - dict_working['state_incentive_by_W']
    dict_working.pop('temp_cost') #Drop the temporary column

    return(dict_working)

def CalculateBatteryIncentives(dict_working):
    dict_working['net_battery_cost'] = 0 # Add blank column for the cost of the battery after incentives
    dict_working['battery_incentives'] = 0 #Add blank column for battery incentives

    # If state has net metering, then we assume the homeowners get batteries, factoring in a 30% IRA federal rebate
    if dict_working['net_metering'] == 0:
        dict_working['net_battery_cost'] = BATTERY_COST*(1-0.3)
        state = dict_working['state'] # Some states have additional rebate programs
        if state == 'CA':
            dict_working['net_battery_cost'] = dict_working['net_battery_cost'] - BATTERY_KWH*150
        elif state == 'HI':
            dict_working['net_battery_cost'] = dict_working['net_battery_cost'] - min(BATTERY_KW*850, 5*850)
        elif state == 'MD':
            dict_working['net_battery_cost'] = dict_working['net_battery_cost'] - min(BATTERY_COST*0.3, 5000)
        elif state == 'OR':
            dict_working['net_battery_cost'] = dict_working['net_battery_cost'] - min(BATTERY_KWH*300, BATTERY_COST*0.4, 2500)
        elif state == 'NV':
            dict_working['net_battery_cost'] = dict_working['net_battery_cost'] - min(BATTERY_KWH*95, BATTERY_COST*0.5, 3000)

        dict_working['battery_incentives'] = BATTERY_COST - dict_working['net_battery_cost']
    
        dict_working['net_estimated_cost'] = dict_working['net_estimated_cost'] + dict_working['net_battery_cost']

    return(dict_working)


def CalculateProductionSavings(dict_working): # CALCULATE PRODUCTION SAVINGS: SAVINGS FROM NET METERING & SRECs
    
    # net metering does not apply to excess production above annual demand. SRECs apply to ALL production
    dict_working['NetMetering_eligible_production'] = min(dict_working['system_output_annual'], dict_working['electricity_use_kwh'])
    dict_working['SREC_eligible_production'] = dict_working['system_output_annual'] if dict_working['net_metering'] == 1 else dict_working['eligible_production']

    # We multiply by 'electricity_price' even where net metering is 0, bc we assume that they get a battery savings are equivalent to the forgone electricity costs
    # FOR STATES WIHTOUT NET METERING: change to just include first half of this equation, ignore SRECs, bc power not being provided to grid, just straight to battery?
    # I CHECKED: in states without net metering, the SREC price is 0
    
    # YEAR 1 production savings
    dict_working['year1_production_savings'] = dict_working['NetMetering_eligible_production'] * dict_working['electricity_price'] + dict_working['SREC_eligible_production'] * dict_working['SREC_USD_kwh']

    # Create a new column called '20_year_production_savings' that is the 20 year production savings, taking into account a 2.2% annual increase in electricity prices
    dict_working['20_year_production_savings'] = 0
    dict_working['TEMP_net_metering_price'] = dict_working['electricity_price']
    
    # YEAR 20 production savings
    year = 1 
    while year <= NET_SAVINGS_YEARS:
        
        dict_working['20_year_production_savings'] = dict_working['20_year_production_savings'] + dict_working['NetMetering_eligible_production'] * dict_working['TEMP_net_metering_price'] + dict_working['SREC_eligible_production'] * dict_working['SREC_USD_kwh']
        
        dict_working['TEMP_net_metering_price'] = dict_working['electricity_price'] * ENERGY_PRICE_GROWTH_RATE**year #Update the price according to the rate of inflation. ** is python for exponent
        
        year += 1

    # ILLINOIS has a complicated REC program where they prepurchase 15 years of recs. SOURCE: https://www.solarreviews.com/blog/illinois-renews-best-solar-incentive
    if dict_working['state'] == 'IL':
        if dict_working['recommended_system_size_(KW)'] <= 10:
            dict_working['20_year_production_savings'] = dict_working['20_year_production_savings'] + (NET_SAVINGS_YEARS*dict_working['system_output_annual']/1000) * (78.51 + 82.22)/2 # For systems <= 10KW, get paid ~$80 per MWh of production over 15 years
        elif dict_working['recommended_system_size_(KW)'] > 10:
            dict_working['20_year_production_savings'] = dict_working['20_year_production_savings'] + (NET_SAVINGS_YEARS*dict_working['system_output_annual']/1000) * (66.39 + 71.89)/2 # For systems <= 10KW, get paid ~$70 per MWh of production over 15 years

    dict_working.pop('TEMP_net_metering_price') #Drop the temporary column

    return(dict_working)

def CalculateLoanPayments(dict_working): 
    dict_working['monthly_interest_payment'] = (dict_working['net_estimated_cost'] * (DEFAULT_INTEREST_RATE/12)) / (1 - (1 + (DEFAULT_INTEREST_RATE/12))**(-12*DEFAULT_LOAN_TERM))
    
    dict_working['yearly_interest_payment'] = dict_working['monthly_interest_payment']*12

    dict_working['year1_net_savings'] = dict_working['year1_production_savings'] - dict_working['yearly_interest_payment']
    
    #if the loan term is greater than the net savings years, then only want to subtract the interest payments for the net savings years
    dict_working['20yr_net_savings']  = dict_working['20_year_production_savings'] - min(DEFAULT_LOAN_TERM, NET_SAVINGS_YEARS) * dict_working['yearly_interest_payment'] 

    return(dict_working)







def CalculatePaybackPeriod(): 
    dict_working = pd.read_csv('1_output.csv')

    dict_working = dict_working.assign(energy_price_growth_rate=ENERGY_PRICE_GROWTH_RATE) #According to the EIA, electricity prices have increased 1.8% per year in the United States for the past 25 years
    #dict_working = dict_working.assign(cumulative_savings=0)
    dict_working['cumulative_savings'] = 0
    dict_working = dict_working.assign(payback_period=None) 

    dict_working['TEMP_net_metering_price'] = dict_working['electricity_price'] #Create a temporary column for the output incentive price, which will be updated each year    

    #Looping through each row, find the payback period for the system
    for index, row in dict_working.iterrows():
        year = 1
        while dict_working['cumulative_savings'] <= dict_working['net_estimated_cost']:
            dict_working['cumulative_savings'] = dict_working['cumulative_savings'] + dict_working['eligible_production'] * dict_working['TEMP_net_metering_price'] + dict_working['output_annual']*dict_working['SREC_USD_kwh']
            dict_working['TEMP_net_metering_price'] = dict_working['electricity_price'] * dict_working['energy_price_growth_rate']**year #For each year, update the price according to the rate of inflation. ** is python for exponent
            year += 1
            if year > 30:
                print('ERROR: Payback period is greater than 30 years.')
                break

        #Update the DataFrame
        dict_working['cumulative_savings'] = dict_working['cumulative_savings']
        dict_working['payback_period'] = year-1
    
    dict_working.drop(columns=['TEMP_net_metering_price'], inplace=True)

    dict_working.to_csv('1_output.csv', index=False)
    print('CalculatePaybackPeriod: 1_output\n')


# Output preparation

def ClearHPdatafromSolar(dict_working, heatpump_query):
    if heatpump_query == False:
        # Overwrite all values in the above keys to be None
        dict_working["status_quo_electricity"] = None
        dict_working["status_quo_natgas"] = None
        dict_working["heatpump_electricity"] = None
        dict_working["natgas_price_USD_per_1000_cf_2021"] = None
        dict_working["cost_before_heatpump"] = None
        dict_working["cost_after_heatpump"] = None
        dict_working["heatpump_savings"] = None
    return(dict_working)

def RoundFields(): 
    dict_working = pd.read_csv('1_output.csv')

    dict_working['capacity_factor']              = dict_working['capacity_factor'].round(3)
    dict_working['electricity_use_kwh']          = dict_working['electricity_use_kwh'].round()
    dict_working['avg_electric_bill_monthly']    = dict_working['avg_electric_bill_monthly'].round()
    dict_working['recommended_system_size_(KW)'] = dict_working['recommended_system_size_(KW)'].round(1)
    dict_working['electricity_price']            = dict_working['electricity_price'].round(3)
    dict_working['estimated_cost']               = dict_working['estimated_cost'].round()
    dict_working['federal_incentive']            = dict_working['federal_incentive'].round()
    dict_working['state_incentive_by_percent']   = dict_working['state_incentive_by_percent'].round()
    dict_working['net_estimated_cost']           = dict_working['net_estimated_cost'].round()
    dict_working['year1_production_savings']     = dict_working['year1_production_savings'].round()
    dict_working['cumulative_savings']           = dict_working['cumulative_savings'].round()
    dict_working['state_incentive_by_W']         = dict_working['state_incentive_by_W'].round()
    dict_working['monthly_interest_payment']     = dict_working['monthly_interest_payment'].round()
    dict_working['yearly_interest_payment']      = dict_working['yearly_interest_payment'].round()
    dict_working['year1_net_savings']            = dict_working['year1_net_savings'].round()
    dict_working['system_output_annual']         = dict_working['system_output_annual'].round()
    dict_working['eligible_production']          = dict_working['eligible_production'].round()
    dict_working['cost_before_heatpump']         = dict_working['cost_before_heatpump'].round()
    dict_working['cost_after_heatpump']          = dict_working['cost_after_heatpump'].round()
    dict_working['heatpump_savings']             = dict_working['heatpump_savings'].round()

    dict_working.to_csv('1_output.csv', index=False)

def DropFields(): 
    dict_working = pd.read_csv('1_output.csv')

    dict_working.drop(columns=['output_annual',
    'sizing_ratio',
    'natgas_price_USD_per_1000_cf_2021',
    'avg_cost_per_kw',
    'W_incentive_max_USD',
    'incentive_per_W',
    'percent_incentive_max_USD',
    'incentive_percent',
    'eligible_production',
    'cumulative_savings'], inplace=True)

    dict_working.to_csv('1_output.csv', index=False)

def RenameFields(): 
    dict_working = pd.read_csv('1_output.csv')

    for column in dict_working.columns:
        dict_working.rename(columns={column:column.capitalize().replace("_"," ")},inplace=True)

    # raname column 'average energy use (kwh)' to 'average energy use (kwh, yearly)'
    dict_working.rename(columns={'Average energy use (kwh)':'Average energy use (kwh, yearly)'},inplace=True)
    dict_working.rename(columns={'Price':'Price ($)'},inplace=True)
    dict_working.rename(columns={'Cost before heatpump':'Utilities before heatpump ($, yearly)'},inplace=True)
    dict_working.rename(columns={'Cost after heatpump':'Utilities after heatpump ($, yearly)'},inplace=True)
    dict_working.rename(columns={'Heatpump savings':'Heatpump savings ($, yearly)'},inplace=True)
    dict_working.rename(columns={'Estimated cost':'Estimated system cost ($)'},inplace=True)
    dict_working.rename(columns={'Srec $ kwh':'Srec ($ per kwh)'},inplace=True)
    dict_working.rename(columns={'Net metering':'Net metering flag'},inplace=True)
    dict_working.rename(columns={'Federal incentive':'Federal tax incentive ($)'},inplace=True)
    dict_working.rename(columns={'State incentive by percent':'State tax incentive ($)'},inplace=True)
    dict_working.rename(columns={'State incentive by w':'State watt incentive ($)'},inplace=True)
    dict_working.rename(columns={'Net estimated cost':'Net estimated cost ($)'},inplace=True)
    dict_working.rename(columns={'System output annual':'System output annual (kwh)'},inplace=True)
    dict_working.rename(columns={'Year1 production savings':'Year 1 production savings ($)'},inplace=True)
    dict_working.rename(columns={'Monthly interest payment':'Monthly interest payment ($)'},inplace=True)
    dict_working.rename(columns={'Yearly interest payment':'Yearly interest payment ($)'},inplace=True)
    dict_working.rename(columns={'Net yearly savings':'Net yearly savings ($)'},inplace=True)

    dict_working.to_csv('1_output.csv', index=False)


#Key assumptions for calculating savings net of loan payments
ENERGY_PRICE_GROWTH_RATE = 1.022
DEFAULT_INTEREST_RATE = 0.06
DEFAULT_LOAN_TERM = 20

BATTERY_COUNT = 1
BATTERY_COST  = 14200 # Tesla Powerwall
BATTERY_KWH   = 13.5 # Tesla Powerwall capacity
BATTERY_KW    = 5 # Tesla Powerwall real power, KW, max continuous (charge and discharge)
BATTERY_COST  = BATTERY_COST * BATTERY_COUNT
BATTERY_KWH   = BATTERY_KWH * BATTERY_COUNT
BATTERY_KW    = BATTERY_KW * BATTERY_COUNT

NET_SAVINGS_YEARS = DEFAULT_LOAN_TERM

if __name__ == "__main__":
    t0 = time.time()