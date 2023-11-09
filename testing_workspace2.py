import json
from Main_vAPI3 import *

zip_query = "60188"
electric_bill_query = 150
sqft_query = None
heatpump_query = False

BATTERY_COUNT = 1
BATTERY_KWH = 13.5

result = PullFromDBmain(zip_query, electric_bill_query, sqft_query, heatpump_query)

#convert result dictioniary to json
result = json.dumps(result)

#pretty print the json
result = json.dumps(json.loads(result), indent=4)

print(result)
