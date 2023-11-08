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
    return(df_working)

def MergeZipLevelDemand(df_working, electric_bill_query):        
    #Calcuate a homeowners electric use based on their electric bill. Else, use the average electric use for the zip code
    if electric_bill_query is not None:
        df_working['electricity_use_kwh'] = (12*electric_bill_query)/df_working['price']
    else:
        df_working['electricity_use_kwh'] = df_working['avg_electricity_use_kwh']
    return(df_working)


# GET heat pump results influx from NREL or Cache

# Call CallHeatPumpAPI() 
# Call MergeCachedKelvinOutput() 

############################## THIS IS WHERE THINGS DEVIATE BASED ON WHETHER THEY ARE GETTING A HEAT PUMP ##############################

def CalculateRecommendedSystemSize(): 
    df_working = pd.read_csv('0_output.csv')

    if net_of_heatpumps == True:
        df_working['electricity_use_kwh'] = df_working['electricity_use_kwh'] + df_working["heatpump_electricity"]
        df_working['Heat pump'] = 'Yes'
        df_working['avg_electric_bill_monthly'] = df_working['electricity_use_kwh']*df_working['electricity_price']/12
    else:
        df_working['Heat pump'] = 'No'

    ############################## THIS IS WHERE THINGS DEVIATE BASED ON WHETHER THE STATE HAS NET METERING OR NOT ##############################

    #This file adds columns: state_name, climata_rank, percent_incentive_max_$, incentive_percent, net_of_federal, SREC_$_kwh, and net_metering
    df_incentives = pd.read_csv('/Users/peterlehner/Dropbox/Climata_GoingSolo/Data/Incentives/state_to_DSIRE_incentives_031823.csv')
    df_incentives = df_incentives[['state', 'net_metering']] # Drop all columns except state and net_metering
    df_working = pd.merge(df_working, df_incentives, on='state', how='left')

    #calculate how much to scale down the size of the solar array IF the system is paired with a battery (in the case of NO net metering)
    df_working['EnergyUse_to_BatterySize'] = df_working['electricity_use_kwh']/(BATTERY_COUNT*13.5*1000) # 13.5 kWh is capacity of a Tesla Powerwall
    df_working['solarWbattery_system_scaling_factor'] = -0.2017*df_working['EnergyUse_to_BatterySize'] + 0.8646 # This linear equation from Battery_sensitivity_analysis.xlsx
    df_working.loc[df_working['net_metering'] == 1, 'solarWbattery_system_scaling_factor'] = 1 # if the value of df_working['net_metering'] == 1, then reset the scaling factor should be 1 (i.e., no scaling)

    #calculate the recommended system size in KW. This is the average energy use in the zip code * the sizing ratio and, IF the battery is included, the solarWbattery_system_scaling_factor
    df_working['recommended_system_size_(KW)'] = df_working['solarWbattery_system_scaling_factor']*df_working['electricity_use_kwh']*df_working['sizing_ratio'] # e.g.: 10,000 KWH * (1 KW / 1000 KWH) = 10 KW.   10 KW * (1000 KWH / 1 KW) = 10,000 KWH

    #take the mininum of the recommended system size and 15 KW because roofs can't fit large arrays
    df_working['recommended_system_size_(KW)'] = df_working['recommended_system_size_(KW)'].apply(lambda x: min(x, 15))

    df_working['system_output_annual'] = df_working['recommended_system_size_(KW)']*df_working['output_annual']

    df_working.to_csv('1_output.csv', index=False)
    print('CalculateRecommendedSystemSize: 1_output\n')

# Merge costs and incentives

def MergeCosts(): 
    df_working['estimated_cost'] = df_working['avg_cost_per_kw']*df_working['recommended_system_size_(KW)']


def MergeIncentivesCalculateGrossSavings(): 
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

#Calculate savings

def CalculateProductionSavings(): 
    df_working = pd.read_csv('1_output.csv')

    # --------------------------------------------- CALCULATE PRODUCTION SAVINGS: SAVINGS FROM NET METERING & SRECs ---------------------------------------------

    # net metering does not apply to excess production above annual demand. SRECs apply to ALL production
    df_working['eligible_production'] = df_working[['system_output_annual','electricity_use_kwh']].min(axis=1)

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

def CalculatePaybackPeriod(): 
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

def CalculateLoanPayments(): 
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




# Output preparation

def ClearHPdatafromSolar():
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

def RoundFields(): 
    df_working = pd.read_csv('1_output.csv')

    df_working['capacity_factor']              = df_working['capacity_factor'].round(3)
    df_working['electricity_use_kwh']      = df_working['electricity_use_kwh'].round()
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

def DropFields(): 
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

def RenameFields(): 
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

RUNTIME_DELAY = False # TURN THIS ON IF RUNNING MORE  THAN 1000 zips per hour

TAKE_SAMPLE = True
NUMBER_OF_ZIPS = 3

if __name__ == "__main__":
    t0 = time.time()

    #This section pulls data that does not differ whether someone has a heat pump or not:

    SelectZipCodes()

    MergeCachedNRELoutput()
    
    MergeZipLevelDemand()

    CalculateSizingRatio()
    
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

        # Output prepartion for each file:
        ClearHPdatafromSolar()
        RoundFields() 
        DropFields()
        RenameFields()

    print(f'\nExecution time (s): {round(time.time() - t0)}')