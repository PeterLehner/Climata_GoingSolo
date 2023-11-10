import json
from Main_v1.0.0 import *

zip_query = "03047"
electric_bill_query = 150
heatpump_query = False
sqft_query = None

result = PullFromDBmain(zip_query, electric_bill_query, sqft_query, heatpump_query)

result = json.dumps(result) #convert result dictioniary to json
result = json.dumps(json.loads(result), indent=4) #pretty print the json

print(result)