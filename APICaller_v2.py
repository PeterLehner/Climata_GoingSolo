from flask import Flask, request
import pandas as pd
from Main_v101 import SavingsModel

df_working = pd.read_csv('Data/database_main.csv')

app = Flask(__name__)

@app.route('/')

def APIRequest(df_working):
    zip_query           = request.args.get('zip_query')
    electric_bill_query = request.args.get('electric_bill_query')
    sqft_query          = request.args.get('sqft_query')
    heatpump_query      = request.args.get('heatpump_query')

    electric_bill_query = float(electric_bill_query) if electric_bill_query is not None else None
    sqft_query          = float(sqft_query) if sqft_query is not None else None

    return SavingsModel(df_working, zip_query, electric_bill_query, sqft_query, heatpump_query)

if __name__ == '__main__':
    app.run(debug=True)