from collections import OrderedDict

#Key assumptions for calculating savings net of loan payments
ENERGY_PRICE_GROWTH_RATE = 1.022
DEFAULT_INTEREST_RATE = 0.06
DEFAULT_LOAN_TERM = 20
NET_SAVINGS_YEARS = DEFAULT_LOAN_TERM # Can be changed

BATTERY_COUNT = 1
BATTERY_COST  = 14200 # Tesla Powerwall
BATTERY_KWH   = 13.5 # Tesla Powerwall capacity
BATTERY_KW    = 5 # Tesla Powerwall real power, KW, max continuous (charge and discharge)
BATTERY_COST  = BATTERY_COST * BATTERY_COUNT
BATTERY_KWH   = BATTERY_KWH * BATTERY_COUNT
BATTERY_KW    = BATTERY_KW * BATTERY_COUNT

#def SavingsModel(df_working, zip_query, electric_bill_query, sqft_query, heatpump_query): 
def SavingsModel(dict_working, zip_query, electric_bill_query, sqft_query, heatpump_query): 

    #df_working = pd.read_csv('Data/database_main.csv')

    #zip_query = int(zip_query)  # Convert to integer
    #dict_working = df_working[df_working['zip'] == zip_query].squeeze().to_dict()  # Read the row with the matching zip_query as a dictionary

    state                             = dict_working.get('state')
    avg_electricity_use_kwh           = dict_working.get('avg_electricity_use_kwh')
    electricity_price                 = dict_working.get('electricity_price')
    output_annual                     = dict_working.get('output_annual')
    sizing_ratio                      = dict_working.get('sizing_ratio')
    #avg_electric_bill_monthly         = dict_working.get('avg_electric_bill_monthly')
    #natgas_price_USD_per_1000_cf_2021 = dict_working.get('natgas_price_USD_per_1000_cf_2021')
    #median_sqft_zip                   = dict_working.get('median_sqft_zip')
    #median_sqft_state                 = dict_working.get('median_sqft_state')
    #median_sqft_country               = dict_working.get('median_sqft_country')
    avg_cost_per_kw                   = dict_working.get('avg_cost_per_kw')
    status_quo_electricity            = dict_working.get('status_quo_electricity')
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

    # Adjust elecrtricity use
    # ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    if electric_bill_query is not None:
        electricity_use_kwh = (12*electric_bill_query)/electricity_price #Calcuate a homeowners electric use based on their electric bill.
    else:
        electricity_use_kwh = avg_electricity_use_kwh # Else, use the average electric use for the zip code


    # Calculate heat pump savings
    # ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    if sqft_query is not None:
        print("TO DO")
        #CallKelvinAPI(dict_working, sqft_query) # If a sqft is passed into API, call the Kelvin model # TO DO
    else: #just use the Kelvin results for the average sqft for the zip code
        cost_before_heatpump = avg_cost_before_heatpump
        cost_after_heatpump = avg_cost_after_heatpump
        heatpump_savings = avg_heatpump_savings


    # Calculate recommended system size
    # ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    if heatpump_query == True:
        electricity_use_kwh = electricity_use_kwh + heatpump_electricity
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


    # Calculate production savings: the savings from net metering and SRECs
    # ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    NetMetering_eligible_production = min(system_output_annual, electricity_use_kwh) # output can be less than use because of 15 KW cap. And net metering does not apply to excess production above annual demand. 
    SREC_eligible_production = system_output_annual if net_metering == 1 else NetMetering_eligible_production # SRECs apply to ALL production, except in states without net metering (I think)
    # FOR STATES WIHTOUT NET METERING: change to just include first half of this equation, ignore SRECs, bc power not being provided to grid, just straight to battery?
    
    # YEAR 1 production savings: equivalent to forgone electricity costs + SREC revenue
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


    # Calculate loan payments and net savings
    # ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    monthly_interest_payment = (net_estimated_cost * (DEFAULT_INTEREST_RATE/12)) / (1 - (1 + (DEFAULT_INTEREST_RATE/12))**(-12*DEFAULT_LOAN_TERM))
    yearly_interest_payment = monthly_interest_payment*12
    year1_net_savings = year1_production_savings - yearly_interest_payment
    _20yr_net_savings  = _20_year_production_savings - min(DEFAULT_LOAN_TERM, NET_SAVINGS_YEARS) * yearly_interest_payment #if the loan term is greater than the net savings years, then only want to subtract the interest payments for the net savings years



    # Prep results for output ----------------------------------------------------------------------------------------------------------------------------------------------------------------
    
    if heatpump_query == False: # Overwrite all values in the above keys to be None
        heatpump_electricity = None
        cost_before_heatpump = None
        cost_after_heatpump = None
        heatpump_savings = None

    # Round the variables with inline if statements
    electricity_use_kwh         = round(electricity_use_kwh) if electricity_use_kwh is not None else electricity_use_kwh
    recommended_system_size_KW  = round(recommended_system_size_KW, 1) if recommended_system_size_KW is not None else recommended_system_size_KW
    system_output_annual        = round(system_output_annual) if system_output_annual is not None else system_output_annual
    
    estimated_cost              = round(estimated_cost) if estimated_cost is not None else estimated_cost
    federal_incentive           = round(federal_incentive) if federal_incentive is not None else federal_incentive
    state_incentive_by_W        = round(state_incentive_by_W) if state_incentive_by_W is not None else state_incentive_by_W
    state_incentive_by_percent  = round(state_incentive_by_percent) if state_incentive_by_percent is not None else state_incentive_by_percent
    net_battery_cost            = round(net_battery_cost) if net_battery_cost is not None else net_battery_cost
    battery_incentives          = round(battery_incentives) if battery_incentives is not None else battery_incentives
    net_estimated_cost          = round(net_estimated_cost) if net_estimated_cost is not None else net_estimated_cost
    
    net_metering                = round(net_metering) if net_metering is not None else net_metering
    year1_production_savings    = round(year1_production_savings) if year1_production_savings is not None else year1_production_savings
    _20_year_production_savings = round(_20_year_production_savings) if _20_year_production_savings is not None else _20_year_production_savings

    yearly_interest_payment     = round(yearly_interest_payment) if yearly_interest_payment is not None else yearly_interest_payment
    year1_net_savings           = round(year1_net_savings) if year1_net_savings is not None else year1_net_savings
    _20yr_net_savings           = round(_20yr_net_savings) if _20yr_net_savings is not None else _20yr_net_savings  # Assuming '_20yr_net_savings' is the cumulative savings
    
    cost_before_heatpump        = round(cost_before_heatpump) if cost_before_heatpump is not None else cost_before_heatpump
    cost_after_heatpump         = round(cost_after_heatpump) if cost_after_heatpump is not None else cost_after_heatpump
    heatpump_savings            = round(heatpump_savings) if heatpump_savings is not None else heatpump_savings

    # result_dict = {
    #     'zip_query'                  : zip_query,
    #     'state'                      : state,
    #     'electric_bill_query'        : electric_bill_query,
    #     'heatpump_query'             : heatpump_query,
    #     'sqft_query'                 : sqft_query,
        
    #     'electricity_use_kwh'        : electricity_use_kwh,
    #     'recommended_system_size_KW' : recommended_system_size_KW,
    #     'system_output_annual'       : system_output_annual,

    #     'estimated_cost'             : estimated_cost,
    #     'federal_incentive'          : federal_incentive,
    #     'state_incentive_by_W'       : state_incentive_by_W,
    #     'state_incentive_by_percent' : state_incentive_by_percent,
    #     'net_battery_cost'           : net_battery_cost,
    #     'battery_incentives'         : battery_incentives,
    #     'net_estimated_cost'         : net_estimated_cost,

    #     'net_metering'               : net_metering,
    #     'year1_production_savings'   : year1_production_savings,
    #     '_20_year_production_savings': _20_year_production_savings,
        
    #     'yearly_interest_payment'    : yearly_interest_payment,
    #     'year1_net_savings'          : year1_net_savings,
    #     '_20yr_net_savings'          : _20yr_net_savings,
        
    #     'Heat_pump'                  : Heat_pump,
    #     'cost_before_heatpump'       : cost_before_heatpump,
    #     'cost_after_heatpump'        : cost_after_heatpump,
    #     'heatpump_savings'           : heatpump_savings,
    # }

    result_JSON = OrderedDict({
        'Section'                        : OrderedDict({
            'zip_query'                  : zip_query,
            'state'                      : state,
            'electric_bill_query'        : electric_bill_query,
            'heatpump_query'             : heatpump_query,
            'sqft_query'                 : sqft_query,
        }),
        'electricity_section'            : OrderedDict({
            'electricity_use_kwh'        : electricity_use_kwh,
            'recommended_system_size_KW' : recommended_system_size_KW,
            'system_output_annual'       : system_output_annual,
        }),
        'cost_section'                   : OrderedDict({
            'estimated_cost'             : estimated_cost,
            'federal_incentive'          : federal_incentive,
            'state_incentive_by_W'       : state_incentive_by_W,
            'state_incentive_by_percent' : state_incentive_by_percent,
            'net_battery_cost'           : net_battery_cost,
            'battery_incentives'         : battery_incentives,
            'net_estimated_cost'         : net_estimated_cost,
        }),
        'savings_section'                : OrderedDict({
            'net_metering'               : net_metering,
            'year1_production_savings'   : year1_production_savings,
            '_20_year_production_savings': _20_year_production_savings,
            'yearly_interest_payment'    : yearly_interest_payment,
            'year1_net_savings'          : year1_net_savings,
            '_20yr_net_savings'          : _20yr_net_savings,
        }),
        'heatpump_section'               : OrderedDict({
            'Heat_pump'                  : Heat_pump,
            'cost_before_heatpump'       : cost_before_heatpump,
            'cost_after_heatpump'        : cost_after_heatpump,
            'heatpump_savings'           : heatpump_savings,
        }),
    })

    return result_JSON