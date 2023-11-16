# Purpose: Process the model output from the savings model and format it for the API response
import json

def process_model_output(savings_model_output_raw):
    ENERGY_PRICE_GROWTH_RATE          = savings_model_output_raw.get('ENERGY_PRICE_GROWTH_RATE')
    TOTAL_SAVINGS_YEARS               = savings_model_output_raw.get('TOTAL_SAVINGS_YEARS')
    DEFAULT_LOAN_TERM                 = savings_model_output_raw.get('DEFAULT_LOAN_TERM')
    DEFAULT_INTEREST_RATE             = savings_model_output_raw.get('DEFAULT_INTEREST_RATE')
    BATTERY_COUNT                     = savings_model_output_raw.get('BATTERY_COUNT')
    BATTERY_COST                      = savings_model_output_raw.get('BATTERY_COST')
    BATTERY_KWH                       = savings_model_output_raw.get('BATTERY_KWH')
    BATTERY_KW                        = savings_model_output_raw.get('BATTERY_KW')
    zip_query                         = savings_model_output_raw.get('zip_query')
    electric_bill_query               = savings_model_output_raw.get('electric_bill_query')
    loan_term_query                   = savings_model_output_raw.get('loan_term_query')
    loan_rate_query                   = savings_model_output_raw.get('loan_rate_query')
    heatpump_query                    = savings_model_output_raw.get('heatpump_query')
    sqft_query                        = savings_model_output_raw.get('sqft_query')
    state                             = savings_model_output_raw.get('state')
    avg_electricity_use_kwh           = savings_model_output_raw.get('avg_electricity_use_kwh')
    electricity_price                 = savings_model_output_raw.get('electricity_price')
    output_annual                     = savings_model_output_raw.get('output_annual')
    sizing_ratio                      = savings_model_output_raw.get('sizing_ratio')
    natgas_price_USD_per_1000_cf_2021 = savings_model_output_raw.get('natgas_price_USD_per_1000_cf_2021')
    median_sqft_zip                   = savings_model_output_raw.get('median_sqft_zip')
    median_sqft_state                 = savings_model_output_raw.get('median_sqft_state')
    median_sqft_country               = savings_model_output_raw.get('median_sqft_country')
    avg_cost_per_kw                   = savings_model_output_raw.get('avg_cost_per_kw')
    status_quo_electricity_cooling    = savings_model_output_raw.get('status_quo_electricity_cooling')
    status_quo_natgas                 = savings_model_output_raw.get('status_quo_natgas')
    heatpump_electricity              = savings_model_output_raw.get('heatpump_electricity')
    avg_cost_before_heatpump          = savings_model_output_raw.get('avg_cost_before_heatpump')
    avg_cost_after_heatpump           = savings_model_output_raw.get('avg_cost_after_heatpump')
    avg_heatpump_savings              = savings_model_output_raw.get('avg_heatpump_savings')
    W_incentive_max_USD               = savings_model_output_raw.get('W_incentive_max_USD')
    incentive_per_W                   = savings_model_output_raw.get('incentive_per_W')
    percent_incentive_max_USD         = savings_model_output_raw.get('percent_incentive_max_USD')
    incentive_percent                 = savings_model_output_raw.get('incentive_percent')
    net_of_federal                    = savings_model_output_raw.get('net_of_federal')
    SREC_USD_kwh                      = savings_model_output_raw.get('SREC_USD_kwh')
    net_metering                      = savings_model_output_raw.get('net_metering')
    loan_term                         = savings_model_output_raw.get('loan_term')
    loan_rate                         = savings_model_output_raw.get('loan_rate')
    electricity_use_kwh               = savings_model_output_raw.get('electricity_use_kwh')
    sqft                              = savings_model_output_raw.get('sqft')
    cost_before_heatpump              = savings_model_output_raw.get('cost_before_heatpump')
    cost_after_heatpump               = savings_model_output_raw.get('cost_after_heatpump')
    heatpump_savings                  = savings_model_output_raw.get('heatpump_savings')
    recommended_system_size_KW        = savings_model_output_raw.get('recommended_system_size_KW')
    system_output_annual              = savings_model_output_raw.get('system_output_annual')
    NetMetering_eligible_production   = savings_model_output_raw.get('NetMetering_eligible_production')
    SREC_eligible_production          = savings_model_output_raw.get('SREC_eligible_production')
    year1_production_savings          = savings_model_output_raw.get('year1_production_savings')
    total_production_savings          = savings_model_output_raw.get('total_production_savings')
    TEMP_net_metering_price           = savings_model_output_raw.get('TEMP_net_metering_price')
    year                              = savings_model_output_raw.get('year')
    estimated_cost                    = savings_model_output_raw.get('estimated_cost')
    federal_incentive                 = savings_model_output_raw.get('federal_incentive')
    temp_cost                         = savings_model_output_raw.get('temp_cost')
    amount_flt                        = savings_model_output_raw.get('amount_flt')
    amount_max                        = savings_model_output_raw.get('amount_max')
    state_incentive_by_W              = savings_model_output_raw.get('state_incentive_by_W')
    state_incentive_by_percent        = savings_model_output_raw.get('state_incentive_by_percent')
    net_estimated_cost                = savings_model_output_raw.get('net_estimated_cost')
    estimated_battery_cost            = savings_model_output_raw.get('estimated_battery_cost')
    battery_incentives                = savings_model_output_raw.get('battery_incentives')
    net_battery_cost                  = savings_model_output_raw.get('net_battery_cost')
    total_incentives                  = savings_model_output_raw.get('total_incentives')
    monthly_interest_payment          = savings_model_output_raw.get('monthly_interest_payment')
    yearly_interest_payment           = savings_model_output_raw.get('yearly_interest_payment')
    year1_net_savings                 = savings_model_output_raw.get('year1_net_savings')
    total_net_savings                 = savings_model_output_raw.get('total_net_savings')
    
        # Prep results for output ----------------------------------------------------------------------------------------------------------------------------------------------------------------
    
    zip_query = str(zip_query).zfill(5) #convert zip_query back to string with length 5 if the integer is only 4 digits
    
    if heatpump_query.lower() == "no":
        heatpump_electricity = None
        cost_before_heatpump = None
        cost_after_heatpump = None
        heatpump_savings = None

    recommended_system_size_KW = round(recommended_system_size_KW, 1) if recommended_system_size_KW is not None else recommended_system_size_KW
    loan_rate                  = round(loan_rate, 3) if loan_rate is not None else loan_rate

    electric_bill_query        = round(electric_bill_query)        if electric_bill_query        is not None else electric_bill_query
    sqft                       = round(sqft)                       if sqft                       is not None else sqft
    electricity_use_kwh        = round(electricity_use_kwh)        if electricity_use_kwh        is not None else electricity_use_kwh
    system_output_annual       = round(system_output_annual)       if system_output_annual       is not None else system_output_annual
    estimated_cost             = round(estimated_cost)             if estimated_cost             is not None else estimated_cost
    federal_incentive          = round(federal_incentive)          if federal_incentive          is not None else federal_incentive
    state_incentive_by_W       = round(state_incentive_by_W)       if state_incentive_by_W       is not None else state_incentive_by_W
    state_incentive_by_percent = round(state_incentive_by_percent) if state_incentive_by_percent is not None else state_incentive_by_percent
    net_battery_cost           = round(net_battery_cost)           if net_battery_cost           is not None else net_battery_cost
    battery_incentives         = round(battery_incentives)         if battery_incentives         is not None else battery_incentives
    net_estimated_cost         = round(net_estimated_cost)         if net_estimated_cost         is not None else net_estimated_cost
    net_metering               = round(net_metering)               if net_metering               is not None else net_metering
    year1_production_savings   = round(year1_production_savings)   if year1_production_savings   is not None else year1_production_savings
    total_production_savings   = round(total_production_savings)   if total_production_savings   is not None else total_production_savings
    loan_term                  = round(loan_term)                  if loan_term                  is not None else loan_term
    monthly_interest_payment   = round(monthly_interest_payment)   if monthly_interest_payment   is not None else monthly_interest_payment
    yearly_interest_payment    = round(yearly_interest_payment)    if yearly_interest_payment    is not None else yearly_interest_payment
    year1_net_savings          = round(year1_net_savings)          if year1_net_savings          is not None else year1_net_savings
    total_net_savings          = round(total_net_savings)          if total_net_savings          is not None else total_net_savings
    cost_before_heatpump       = round(cost_before_heatpump)       if cost_before_heatpump       is not None else cost_before_heatpump
    cost_after_heatpump        = round(cost_after_heatpump)        if cost_after_heatpump        is not None else cost_after_heatpump
    heatpump_savings           = round(heatpump_savings)           if heatpump_savings           is not None else heatpump_savings
    total_incentives           = round(total_incentives)           if total_incentives           is not None else total_incentives

    result_JSON                                 = {
        'query'                                 : {
            'zip'                               : zip_query,
            'solar'                             : {
                'electric_bill'                 : electric_bill_query,
                'loan_term'                     : loan_term_query,
                'loan_rate'                     : loan_rate_query,
                },
            'heatpump'                          : {
                'heatpump'                      : heatpump_query,
                'square_footage'                : sqft_query,
            },
        },
        'location'                              : {
            'state'                             : state,
        },
        'electricity_section'                   : {
            'electricity_use_kwh'               : electricity_use_kwh,
        },
        'solar'                                 : {
            'recommended_solar_size'            : recommended_system_size_KW,
            'system_output_annual'              : system_output_annual,
            'net_metering'                      : 'yes' if net_metering == 1 else 'no',
            'has_battery'                       : 'yes' if net_metering == 0 else 'no',
            'cost_detail'                       : {
                'estimated_solar_cost'          : estimated_cost,
                'estimated_battery_cost'        : estimated_battery_cost,
                'incentives'                    : {
                    'federal_incentive'         : federal_incentive,
                    'state_incentive_by_watt'   : state_incentive_by_W,
                    'state_incentive_by_percent': state_incentive_by_percent,
                    'battery_incentives'        : battery_incentives,
                    'total_incentives'          : total_incentives,
                },
                'net_battery_cost'              : net_battery_cost,
                'net_solar_cost'                : net_estimated_cost - net_battery_cost,
                'net_system_cost'               : net_estimated_cost,
            },
            'loan_detail'                       : {
                'loan_amount'                   : net_estimated_cost,
                'loan_term'                     : loan_term,
                'interest_rate'                 : loan_rate,
                'monthly_interest_payment'      : monthly_interest_payment,
                'yearly_interest_payment'       : yearly_interest_payment,
                },
            'savings_detail'                    : {
                'production_savings'            : [
                    {
                        'year' : 1,
                        'value': year1_production_savings,
                    },
                    {
                        'year' : TOTAL_SAVINGS_YEARS,
                        'value': total_production_savings,
                    },
                ],
                'net_savings': [
                    {
                        'year' : 1,
                        'value': year1_net_savings,
                    },
                    {
                        'year' : TOTAL_SAVINGS_YEARS,
                        'value': total_net_savings,
                    },
                ],
                
            },
        },
        'heatpump'                     : {
            'heat_pump'                : heatpump_query,
            'square_footage'           : sqft,
            'heating_fuel'             : 'natural_gas',
            'hvac_cost_before_heatpump': cost_before_heatpump,
            'hvac_cost_after_heatpump' : cost_after_heatpump,
            'heatpump_savings'         : heatpump_savings,
        },
    }

    result_JSON_final = json.dumps(result_JSON, indent=4)

    return result_JSON_final