from flask import Flask, request
import pandas as pd
from Main_v101 import SavingsModel
import time

df_working = pd.read_csv('Data/database_main.csv')

app = Flask(__name__)

@app.route('/')

def APIRequest():
    t0 = time.time()
    
    zip_query           = request.args.get('zip_query')
    electric_bill_query = request.args.get('electric_bill_query')
    sqft_query          = request.args.get('sqft_query')
    heatpump_query      = request.args.get('heatpump_query')
    t1 = time.time()

    electric_bill_query = float(electric_bill_query) if electric_bill_query is not None else None
    sqft_query          = float(sqft_query) if sqft_query is not None else None
    t2 = time.time()

    zip_query = int(zip_query)  # Convert to integer
    dict_working = df_working[df_working['zip'] == zip_query].squeeze().to_dict()  # Read the row with the matching zip_query as a dictionary
    t3 = time.time()

    SavingsModelOutput = SavingsModel(dict_working, zip_query, electric_bill_query, sqft_query, heatpump_query)
    t4 = time.time()

    t1_t0 = t1-t0
    t2_t1 = t2-t1
    t3_t2 = t3-t2
    t_4_t3 = t4-t3

    time_dict = {
        't1_t0' : t1_t0,
        't2_t1' : t2_t1,
        't3_t2' : t3_t2,
        't_4_t3' : t_4_t3,
    }

    return time_dict

if __name__ == '__main__':
    app.run(debug=True)