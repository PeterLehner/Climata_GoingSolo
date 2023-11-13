from flask import Flask, request
from Main_v101 import SavingsModel
import pandas as pd
import time

df_working = pd.read_csv('Data/database_main.csv')

app = Flask(__name__)
@app.route('/')

def APIRequest():
    t_start = time.time()
    
    # Get the query parameters from the URL
    zip_query           = request.args.get('zip_query')
    electric_bill_query = request.args.get('electric_bill_query')
    loan_term_query     = request.args.get('loan_term_query') # In years
    loan_rate_query     = request.args.get('loan_rate_query') # e.g,. 0.06 for 6%
    sqft_query          = request.args.get('sqft_query')
    heatpump_query      = request.args.get('heatpump_query') # "yes" or "no"

    # Error handling
    if zip_query is None:
        return "Error: zip code is None"
    
    # Correct data types
    zip_query           = int(zip_query) if zip_query is not None else None
    electric_bill_query = float(electric_bill_query) if electric_bill_query is not None else None
    sqft_query          = float(sqft_query) if sqft_query is not None else None
    
    heatpump_query = heatpump_query if heatpump_query is not None else "no"

    dict_working = df_working[df_working['zip'] == zip_query].squeeze().to_dict()  # Read the row with the matching zip_query as a dictionary

    SavingsModelOutput = SavingsModel(dict_working, zip_query, electric_bill_query, loan_term_query, loan_rate_query, heatpump_query, sqft_query)
    
    run_time = t_start-time.time()
    time_dict = {'Function run time' : run_time,}
    #return time_dict

    return SavingsModelOutput

if __name__ == '__main__':
    app.run(debug=False) #TURN OFF DEBUG IN PRODUCTION