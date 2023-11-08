from flask import *
import json, time
from API_Main import *

zip_query = '02340'
electric_bill_query = 125
heatpump_query = True


net_savings_for_API, heatpump_savings, total_upfront_incentives = main(zip_query, heatpump_query, electric_bill_query)