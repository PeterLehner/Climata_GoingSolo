from flask import Flask, request
from Main_v101 import SavingsModel
import pandas as pd
import time
from collections import OrderedDict

DEFAULT_LOAN_TERM = 20
DEFAULT_INTEREST_RATE = 0.06

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

    # Convert the query parameters to the correct data type
    zip_query           = int(zip_query) if zip_query is not None else None
    electric_bill_query = float(electric_bill_query) if electric_bill_query is not None else None
    sqft_query          = float(sqft_query) if sqft_query is not None else None
    loan_term_query     = float(loan_term_query) if loan_term_query is not None else DEFAULT_LOAN_TERM
    loan_rate_query     = float(loan_rate_query) if loan_rate_query is not None else DEFAULT_INTEREST_RATE

    # Filter the dataframe to only the rows with the matching zip_query
    dict_working = df_working[df_working['zip'] == zip_query].squeeze().to_dict()  # Read the row with the matching zip_query as a dictionary

    loan_term_query     = float(loan_term_query) if loan_term_query is not None else DEFAULT_LOAN_TERM
    SavingsModelOutput = SavingsModel(dict_working, zip_query, electric_bill_query, loan_term_query, loan_rate_query, heatpump_query, sqft_query)
    
    # Calculate the run time of the function
    run_time = t_start-time.time()
    time_dict = {'Function run time' : run_time,}

    #return {'SavingsModelOutput': SavingsModelOutput, 'time_dict': time_dict}
    return SavingsModelOutput

if __name__ == '__main__':
    app.run(debug=True) #TURN OFF DEBUG IN PRODUCTION