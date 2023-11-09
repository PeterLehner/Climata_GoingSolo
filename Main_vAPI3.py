import pandas as pd
import numpy as np
from Heatpumps import CallHeatPumpAPI
from MergeCachedKelvinOutput import MergeCachedKelvinOutput

#Key assumptions for calculating savings net of loan payments
ENERGY_PRICE_GROWTH_RATE = 1.022
DEFAULT_INTEREST_RATE = 0.06
DEFAULT_LOAN_TERM = 20
NET_SAVINGS_YEARS = DEFAULT_LOAN_TERM

BATTERY_COUNT = 1
BATTERY_COST  = 14200 # Tesla Powerwall
BATTERY_KWH   = 13.5 # Tesla Powerwall capacity
BATTERY_KW    = 5 # Tesla Powerwall real power, KW, max continuous (charge and discharge)
BATTERY_COST  = BATTERY_COST * BATTERY_COUNT
BATTERY_KWH   = BATTERY_KWH * BATTERY_COUNT
BATTERY_KW    = BATTERY_KW * BATTERY_COUNT

def PullFromDBmain(zip_query, electric_bill_query, sqft_query, heatpump_query): 
    df_working = pd.read_csv('/Users/peterlehner/Dropbox/Climata_GoingSolo/Data/database_main.csv')
    zip_query = int(zip_query)  # Convert to integer
    dict_working = df_working[df_working['zip'] == zip_query].squeeze().to_dict()  # Read the row with the matching zip_query as a dictionary

    zip                               = dict_working.get('zip')
    #lat                               = dict_working.get('lat')
    #lon                               = dict_working.get('lon')
    state                             = dict_working.get('state')
    #LEVEL_avg_electricity_use_kwh     = dict_working.get('LEVEL_avg_electricity_use_kwh')
    avg_electricity_use_kwh           = dict_working.get('avg_electricity_use_kwh')
    #LEVEL_electricity_price           = dict_working.get('LEVEL_electricity_price')
    #electricity_price_old             = dict_working.get('electricity_price_old')
    electricity_price                 = dict_working.get('electricity_price')
    #avg_electric_bill_monthly         = dict_working.get('avg_electric_bill_monthly')
    #LEVEL_natgas_price                = dict_working.get('LEVEL_natgas_price')
    #natgas_price_USD_per_1000_cf_2021 = dict_working.get('natgas_price_USD_per_1000_cf_2021')
    #LEVEL_output_annual               = dict_working.get('LEVEL_output_annual')
    output_annual                     = dict_working.get('output_annual')
    sizing_ratio                      = dict_working.get('sizing_ratio')
    #capacity_factor                   = dict_working.get('capacity_factor')
    #median_sqft_zip                   = dict_working.get('median_sqft_zip')
    #median_sqft_state                 = dict_working.get('median_sqft_state')
    #median_sqft_country               = dict_working.get('median_sqft_country')
    #LEVEL_avg_cost_per_kw             = dict_working.get('LEVEL_avg_cost_per_kw')
    avg_cost_per_kw                   = dict_working.get('avg_cost_per_kw')
    status_quo_electricity            = dict_working.get('status_quo_electricity')
    status_quo_natgas                 = dict_working.get('status_quo_natgas')
    heatpump_electricity              = dict_working.get('heatpump_electricity')
    avg_cost_before_heatpump          = dict_working.get('avg_cost_before_heatpump')
    avg_cost_after_heatpump           = dict_working.get('avg_cost_after_heatpump')
    avg_heatpump_savings              = dict_working.get('avg_heatpump_savings')
    #LEVEL_incentives                  = dict_working.get('LEVEL_incentives')
    W_incentive_max_USD               = dict_working.get('W_incentive_max_USD')
    incentive_per_W                   = dict_working.get('incentive_per_W')
    percent_incentive_max_USD         = dict_working.get('percent_incentive_max_USD')
    incentive_percent                 = dict_working.get('incentive_percent')
    net_of_federal                    = dict_working.get('net_of_federal')
    SREC_USD_kwh                      = dict_working.get('SREC_USD_kwh')
    net_metering                      = dict_working.get('net_metering')


    ### SECTION ### AdjustElectricityUse
    #Calcuate a homeowners electric use based on their electric bill. Else, use the average electric use for the zip code
    if electric_bill_query is not None:
        electricity_use_kwh = (12*electric_bill_query)/electricity_price
    else:
        electricity_use_kwh = avg_electricity_use_kwh


    ### SECTION ### GetHeatpumpSavings
    if sqft_query is not None:
        print("TO DO")
        #CallKelvinAPI(dict_working, sqft_query) ---------------------- TO DO
        # If a sqft is passed into API, call the Kelvin model
    else: #just use the Kelvin results for the average sqft for the zip code
        cost_before_heatpump = avg_cost_before_heatpump
        cost_after_heatpump = avg_cost_after_heatpump
        heatpump_savings = avg_heatpump_savings


    ### SECTION ### CalculateRecommendedSystemSize
    if heatpump_query == True:
        electricity_use_kwh = electricity_use_kwh + dict_working["heatpump_electricity"]
        Heat_pump = 'Yes'
        avg_electric_bill_monthly = electricity_use_kwh*electricity_price/12
    else:
        Heat_pump = 'No'

    if net_metering == 1: #If the state has net metering...
        recommended_system_size_KW = electricity_use_kwh * sizing_ratio # e.g.: ~10,000 KWH * (1 KW / ~1000 KWH) = ~10 KW
    else: # If the state doesn't have net metering, calculate how much to scale down the size of the solar array IF the system is paired with a battery (in the case of NO net metering)   
        EnergyUse_to_BatterySize = electricity_use_kwh / (BATTERY_COUNT * BATTERY_KWH * 1000)
        solarWbattery_system_scaling_factor = -0.2017 * EnergyUse_to_BatterySize + 0.8646  # This linear equation from Battery_sensitivity_analysis.xlsx
        recommended_system_size_KW = solarWbattery_system_scaling_factor * electricity_use_kwh * sizing_ratio

    recommended_system_size_KW = min(recommended_system_size_KW,15) #take the mininum of the recommended system size and 15 KW because roofs can't fit large arrays

    system_output_annual = recommended_system_size_KW*output_annual

    

    ### SECTION ### MergeCosts(dict_working): 
    estimated_cost = avg_cost_per_kw*recommended_system_size_KW
    

    ### SECTION ### CalculateSolarIncentives(dict_working): 
    
    #FEDERAL: Tax credit is 30% of system cost
    federal_incentive = 0.3*estimated_cost

    #create a temporary column for the cost of the system NET of the federal tax credit (for applicable states, of course)
    temp_cost = estimated_cost*0.7 if net_of_federal == 1 else estimated_cost
    
    #STATE: Incentive by watt of installed capacity
    amount_flt = incentive_per_W*(1000*recommended_system_size_KW)
    amount_max = W_incentive_max_USD
    amount_max = float('inf') if amount_max == 0 else amount_max #if amount_max is 0, then set it to infinity so that it is not the min
    state_incentive_by_W = min(amount_flt, amount_max) #if there is no incentive per W, then just take the lump sum in the max column

    #STATE: Incentive by percent of system cost
    amount_flt = incentive_percent*temp_cost #if there is no max, just take the incentive percent multiplied by the system cost
    amount_max = percent_incentive_max_USD
    amount_max = float('inf') if amount_max == 0 else amount_max #if amount_max is 0, then set it to infinity so that it is not the min
    state_incentive_by_percent = min([amount_flt, amount_max]) #if there is no incentive percent, then just take the lump sum in the max column

    #Subtract incentives from system cost to get net cost
    net_estimated_cost = estimated_cost - federal_incentive - state_incentive_by_percent - state_incentive_by_W

    

    ### SECTION ### CalculateBatteryIncentives(dict_working):
    net_battery_cost = 0 # Add blank column for the cost of the battery after incentives
    battery_incentives = 0 #Add blank column for battery incentives

    # If state has net metering, then we assume the homeowners get batteries, factoring in a 30% IRA federal rebate
    if net_metering == 0:
        net_battery_cost = BATTERY_COST*(1-0.3)
        state = state # Some states have additional rebate programs
        if state == 'CA':
            net_battery_cost = net_battery_cost - BATTERY_KWH*150
        elif state == 'HI':
            net_battery_cost = net_battery_cost - min(BATTERY_KW*850, 5*850)
        elif state == 'MD':
            net_battery_cost = net_battery_cost - min(BATTERY_COST*0.3, 5000)
        elif state == 'OR':
            net_battery_cost = net_battery_cost - min(BATTERY_KWH*300, BATTERY_COST*0.4, 2500)
        elif state == 'NV':
            net_battery_cost = net_battery_cost - min(BATTERY_KWH*95, BATTERY_COST*0.5, 3000)

        battery_incentives = BATTERY_COST - net_battery_cost
    
        net_estimated_cost = net_estimated_cost + net_battery_cost


    ### SECTION ### CalculateProductionSavings: savings from net metering and SRECs
    
    # net metering does not apply to excess production above annual demand. SRECs apply to ALL production
    NetMetering_eligible_production = min(system_output_annual, electricity_use_kwh)
    SREC_eligible_production = system_output_annual if net_metering == 1 else NetMetering_eligible_production

    # We multiply by 'electricity_price' even where net metering is 0, bc we assume that they get a battery savings are equivalent to the forgone electricity costs
    # FOR STATES WIHTOUT NET METERING: change to just include first half of this equation, ignore SRECs, bc power not being provided to grid, just straight to battery?
    # I CHECKED: in states without net metering, the SREC price is 0
    
    # YEAR 1 production savings
    year1_production_savings = NetMetering_eligible_production * electricity_price + SREC_eligible_production * SREC_USD_kwh

    # Create a new column called '_20_year_production_savings' that is the 20 year production savings, taking into account a 2.2% annual increase in electricity prices
    _20_year_production_savings = 0
    TEMP_net_metering_price = electricity_price
    
    # YEAR 20 production savings
    year = 1 
    while year <= NET_SAVINGS_YEARS:
        
        _20_year_production_savings = _20_year_production_savings + NetMetering_eligible_production * TEMP_net_metering_price + SREC_eligible_production * SREC_USD_kwh
        
        TEMP_net_metering_price = electricity_price * ENERGY_PRICE_GROWTH_RATE**year #Update the price according to the rate of inflation. ** is python for exponent
        
        year += 1

    # ILLINOIS has a complicated REC program where they prepurchase 15 years of recs. SOURCE: https://www.solarreviews.com/blog/illinois-renews-best-solar-incentive
    if state == 'IL':
        if recommended_system_size_KW <= 10:
            _20_year_production_savings = _20_year_production_savings + (NET_SAVINGS_YEARS*system_output_annual/1000) * (78.51 + 82.22)/2 # For systems <= 10KW, get paid ~$80 per MWh of production over 15 years
        elif recommended_system_size_KW > 10:
            _20_year_production_savings = _20_year_production_savings + (NET_SAVINGS_YEARS*system_output_annual/1000) * (66.39 + 71.89)/2 # For systems <= 10KW, get paid ~$70 per MWh of production over 15 years

    

    ### SECTION ### CalculateLoanPayments
    monthly_interest_payment = (net_estimated_cost * (DEFAULT_INTEREST_RATE/12)) / (1 - (1 + (DEFAULT_INTEREST_RATE/12))**(-12*DEFAULT_LOAN_TERM))
    
    yearly_interest_payment = monthly_interest_payment*12

    year1_net_savings = year1_production_savings - yearly_interest_payment
    
    #if the loan term is greater than the net savings years, then only want to subtract the interest payments for the net savings years
    _20yr_net_savings  = _20_year_production_savings - min(DEFAULT_LOAN_TERM, NET_SAVINGS_YEARS) * yearly_interest_payment 

    return(dict_working)