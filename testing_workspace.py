import json
#from Main_vAPI import PullFromDBmain, AdjustElectricityUse, GetHeatpumpSavings, CalculateRecommendedSystemSize, MergeCosts, CalculateSolarIncentives, CalculateBatteryIncentives, CalculateProductionSavings
from Main_vAPI import *


# Test the SelectZipC83301function
zip_query = "60188"
electric_bill_query = 150
sqft_query = None
heatpump_query = False

BATTERY_COUNT = 1
BATTERY_KWH = 13.5

result = PullFromDBmain(zip_query)

result = AdjustElectricityUse(result, electric_bill_query)

result = GetHeatpumpSavings(result, sqft_query)

result = CalculateRecommendedSystemSize(result, heatpump_query, BATTERY_COUNT, BATTERY_KWH)

result = MergeCosts(result)

result = CalculateSolarIncentives(result)

result = CalculateBatteryIncentives(result)

result = CalculateProductionSavings(result)

result = CalculateLoanPayments(result)

#convert result dictioniary to json
result = json.dumps(result)

#pretty print the json
result = json.dumps(json.loads(result), indent=4)

print(result)
