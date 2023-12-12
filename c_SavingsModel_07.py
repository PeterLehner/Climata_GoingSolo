import pandas as pd
from d_CallHeatpumpAPI_01 import call_heapump_api
import numpy as np

#Key assumptions for calculating savings net of loan payments
ENERGY_PRICE_GROWTH_RATE = 1.022
TOTAL_SAVINGS_YEARS = 20
DEFAULT_LOAN_TERM = 20
DEFAULT_INTEREST_RATE = 0.09

SLOPE_SQFT2KWH = 2.5286
SLOPE_KWH2SQFT = 0.0796


BATTERY_COUNT = 1
BATTERY_COST  = 14200 # Tesla Powerwall
BATTERY_KWH   = 13.5 # Tesla Powerwall capacity
BATTERY_KW    = 5 # Tesla Powerwall real power, KW, max continuous (charge and discharge)
BATTERY_COST  = BATTERY_COST * BATTERY_COUNT
BATTERY_KWH   = BATTERY_KWH * BATTERY_COUNT
BATTERY_KW    = BATTERY_KW * BATTERY_COUNT

def calculate_savings(dict_working, zip_query, electric_bill_query, loan_term_query, loan_rate_query, heatpump_query, sqft_query): 
    state                             = dict_working.get('state')
    avg_electricity_use_kwh           = dict_working.get('avg_electricity_use_kwh')
    electricity_price                 = dict_working.get('electricity_price')
    output_annual                     = dict_working.get('output_annual')
    sizing_ratio                      = dict_working.get('sizing_ratio')
    avg_electric_bill_monthly        = dict_working.get('avg_electric_bill_monthly')
    natgas_price_USD_per_1000_cf_2021 = dict_working.get('natgas_price_USD_per_1000_cf_2021')
    median_sqft_zip                   = dict_working.get('median_sqft_zip')
    median_sqft_state                 = dict_working.get('median_sqft_state')
    median_sqft_country               = dict_working.get('median_sqft_country')
    avg_cost_per_kw                   = dict_working.get('avg_cost_per_kw')
    status_quo_electricity_cooling    = dict_working.get('status_quo_electricity')
    status_quo_natgas                 = dict_working.get('status_quo_natgas')
    heatpump_electricity              = dict_working.get('heatpump_electricity')
    avg_cost_before_heatpump          = dict_working.get('avg_cost_before_heatpump')
    avg_cost_after_heatpump           = dict_working.get('avg_cost_after_heatpump')
    avg_heatpump_savings              = dict_working.get('avg_heatpump_savings')
    W_incentive_max_USD               = dict_working.get('W_incentive_max_USD')
    incentive_per_W                   = dict_working.get('incentive_per_W')
    percent_incentive_max_USD         = dict_working.get('percent_incentive_max_USD')
    incentive_percent                 = dict_working.get('incentive_percent')
    net_of_federal                    = dict_working.get('net_of_federal')
    SREC_USD_kwh                      = dict_working.get('SREC_USD_kwh')
    net_metering                      = dict_working.get('net_metering')

    loan_term = float(loan_term_query) if loan_term_query is not None else DEFAULT_LOAN_TERM
    loan_rate = float(loan_rate_query) if loan_rate_query is not None else DEFAULT_INTEREST_RATE

    # Find the most granular median square footage data available
    if median_sqft_zip is not None and not np.isnan(median_sqft_zip):
        median_sqft = median_sqft_zip
    elif median_sqft_state is not None and not np.isnan(median_sqft_state):
        median_sqft = median_sqft_state
    else:
        median_sqft = median_sqft_country

    # Set electric use
    # ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    if electric_bill_query is not None:
        electricity_use_kwh = (12*electric_bill_query)/electricity_price #Calcuate a homeowners electric use based on their electric bill.
    elif electric_bill_query is None and sqft_query is not None: # If the user entered a square footage but NOT an electric bill, then use the square footage to estimate the electric use
        # Use RECs survey to get slope, but EIA data to get average electricity use by state 
        # Therefore, move set intercept using point: (median_sqft, avg_electricity_use_kwh)
        intercept = avg_electricity_use_kwh - SLOPE_SQFT2KWH*median_sqft
        electricity_use_kwh = SLOPE_SQFT2KWH*sqft_query + intercept
        electricity_use_kwh = max(electricity_use_kwh, avg_electricity_use_kwh*0.25) # If estimated electric use is less than 25% of the average, then set it to 25% of the average
        electricity_use_kwh = min(electricity_use_kwh, avg_electricity_use_kwh*2) # If estimated electric use is greater than 200% of the average, then set it to 200% of the average

        print(f"median_sqft: {median_sqft}")
        print(f'sqft_query: {sqft_query}')
        print(f"avg_electricity_use_kwh: {avg_electricity_use_kwh}")
        print(f"electricity_use_kwh: {round(electricity_use_kwh,0)}")
    else:
        electricity_use_kwh = avg_electricity_use_kwh # Else, use the average electric use for the zip code

    # Set square footage
    # ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    if sqft_query is None or np.isnan(sqft_query): # If the user did NOT enter a square footage...
        # Use RECs survey to get slope, but EIA data to get average electricity use by state 
        # Therefore, move set intercept using point: (avg_electricity_use_kwh, median_sqft)
        intercept = median_sqft - SLOPE_KWH2SQFT*avg_electricity_use_kwh
        sqft = SLOPE_KWH2SQFT*electricity_use_kwh + intercept
        sqft = max(sqft, median_sqft*0.25) 
        sqft = min(sqft, median_sqft*3)

        print(f"avg_electric_bill_monthly: {round(avg_electric_bill_monthly,0)}")
        print(f"INPUT electric_bill_query: {electric_bill_query}")
        print("\n")
        print(f"avg_electricity_use_kwh  : {avg_electricity_use_kwh}")
        print(f"INPUT electricity_use_kwh: {round(electricity_use_kwh,0)}")
        print("\n")
        print(f"median_sqft : {median_sqft}")
        print(f"OUTPUT: sqft: {round(sqft,0)}")
    else:
        sqft = sqft_query

    # Calculate heat pump savings
    # ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    if heatpump_query == 'yes':
        result_tuple = call_heapump_api(zip_query, sqft, electricity_price, natgas_price_USD_per_1000_cf_2021)
        status_quo_electricity_cooling = result_tuple[0]
        status_quo_natgas              = result_tuple[1]
        cost_before_heatpump           = result_tuple[2]
        heatpump_electricity           = result_tuple[3]
        cost_after_heatpump            = result_tuple[4]
        heatpump_savings               = result_tuple[5]
    else: #just use the Kelvin results for the average sqft for the zip code
        cost_before_heatpump = avg_cost_before_heatpump
        cost_after_heatpump = avg_cost_after_heatpump
        heatpump_savings = avg_heatpump_savings


    # Calculate recommended system size
    # ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    if heatpump_query.lower() == "yes":
        electricity_use_kwh = electricity_use_kwh + heatpump_electricity
        avg_electric_bill_monthly = electricity_use_kwh*electricity_price/12

    if net_metering == 1: #If the state has net metering...
        recommended_system_size_KW = electricity_use_kwh * sizing_ratio # e.g.: ~10,000 KWH * (1 KW / ~1000 KWH) = ~10 KW
    else: # If the state doesn't have net metering, calculate how much to scale down the size of the solar array IF the system is paired with a battery (in the case of NO net metering)   
        EnergyUse_to_BatterySize = electricity_use_kwh / (BATTERY_COUNT * BATTERY_KWH * 1000)
        solarWbattery_system_scaling_factor = -0.2017 * EnergyUse_to_BatterySize + 0.8646  # This linear equation from Battery_sensitivity_analysis.xlsx
        recommended_system_size_KW = solarWbattery_system_scaling_factor * electricity_use_kwh * sizing_ratio

    recommended_system_size_KW = min(recommended_system_size_KW,15) #take the mininum of the recommended system size and 15 KW because roofs can't fit large arrays
    system_output_annual = recommended_system_size_KW*output_annual


    # Calculate production savings: the savings from net metering and SRECs
    # ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    NetMetering_eligible_production = min(system_output_annual, electricity_use_kwh) # output can be less than use because of 15 KW cap. And net metering does not apply to excess production above annual demand. 
    SREC_eligible_production = system_output_annual if net_metering == 1 else NetMetering_eligible_production # SRECs apply to ALL production, except in states without net metering (I think)
    # FOR STATES WIHTOUT NET METERING: change to just include first half of this equation, ignore SRECs, bc power not being provided to grid, just straight to battery?
    
    # YEAR 1 production savings: equivalent to forgone electricity costs + SREC revenue
    year1_production_savings = NetMetering_eligible_production * electricity_price + SREC_eligible_production * SREC_USD_kwh

    # Create a new column called 'total_production_savings' that is the 20 year production savings, taking into account a 2.2% annual increase in electricity prices
    total_production_savings = 0
    TEMP_net_metering_price = electricity_price
    
    # YEAR 20 production savings
    year = 1 
    while year <= TOTAL_SAVINGS_YEARS:
        total_production_savings = total_production_savings + NetMetering_eligible_production * TEMP_net_metering_price + SREC_eligible_production * SREC_USD_kwh
        TEMP_net_metering_price = electricity_price * ENERGY_PRICE_GROWTH_RATE**year #Update the price according to the rate of inflation. ** is python for exponent
        year += 1

    # ILLINOIS has a complicated REC program where they prepurchase 15 years of recs. SOURCE: https://www.solarreviews.com/blog/illinois-renews-best-solar-incentive
    if state == 'IL':
        if recommended_system_size_KW <= 10:
            total_production_savings = total_production_savings + (TOTAL_SAVINGS_YEARS*system_output_annual/1000) * (78.51 + 82.22)/2 # For systems <= 10KW, get paid ~$80 per MWh of production over 15 years
        elif recommended_system_size_KW > 10:
            total_production_savings = total_production_savings + (TOTAL_SAVINGS_YEARS*system_output_annual/1000) * (66.39 + 71.89)/2 # For systems <= 10KW, get paid ~$70 per MWh of production over 15 years


    # Calculate system cost, net of solar incentives
    # ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    estimated_cost = avg_cost_per_kw*recommended_system_size_KW
    
    #FEDERAL: Tax credit is 30% of system cost
    federal_incentive = 0.3*estimated_cost 
    temp_cost = estimated_cost*0.7 if net_of_federal == 1 else estimated_cost #create a temporary column for the cost of the system NET of the federal tax credit (for applicable states, of course)
    
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


    # Calculate system cost, net of battery incentives
    # ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    estimated_battery_cost = 0
    battery_incentives = 0 #Add blank column for battery incentives
    net_battery_cost = 0 # Add blank column for the cost of the battery after incentives

    # If state doesn't have net metering, we assume the homeowner gets batterie. Some states have additional rebate programs
    if net_metering == 0:
        estimated_battery_cost = BATTERY_COST
        net_battery_cost = BATTERY_COST*(1-0.3) #30% IRA rebae
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
    total_incentives   = federal_incentive + state_incentive_by_percent + state_incentive_by_W + battery_incentives


    # Calculate loan payments and net savings
    # ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    monthly_interest_payment = (net_estimated_cost * (loan_rate/12)) / (1 - (1 + (loan_rate/12))**(-12*loan_term))
    yearly_interest_payment = monthly_interest_payment*12
    year1_net_savings = year1_production_savings - yearly_interest_payment
    total_net_savings  = total_production_savings - min(loan_term, TOTAL_SAVINGS_YEARS) * yearly_interest_payment #if the loan term is greater than the net savings years, then only want to subtract the interest payments for the net savings years


    savings_model_output_raw = {**globals(), **locals()} #Create a dictionary of all variables using locals() and globals()
    return savings_model_output_raw