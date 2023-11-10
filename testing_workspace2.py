import json
from Main_v100 import *
#from TEMP_error import *
import pandas as pd


electric_bill_query = 150
#electric_bill_query = None
heatpump_query = False
sqft_query = None


#read in zip codes from file zip_lat_lon_state.csv
zip_lat_lon_state = pd.read_csv('Data/Zips/zip_lat_lon_state.csv')

#The first column of this file is name "zip" and contains the zip codes. Pull 10 random zip codes from this column and put into a list
zip_list = zip_lat_lon_state['zip'].sample(n=25).tolist()

#loop through the list of zip codes and run the SavingsModel function on each zip code
for zip_query in zip_list:
    result = SavingsModel(zip_query, electric_bill_query, sqft_query, heatpump_query)

# zip_query = "03047"
# result = SavingsModel(zip_query, electric_bill_query, sqft_query, heatpump_query)

#result = json.dumps(result) #convert result dictioniary to json
#result = json.dumps(json.loads(result), indent=4) #pretty print the json

#print(result)