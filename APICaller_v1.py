# app.py
from flask import Flask, request
from Main_v100 import SavingsModel

app = Flask(__name__)

@app.route('/')

def APIRequest():
    zip_query           = request.args.get('zip_query')
    electric_bill_query = request.args.get('electric_bill_query')
    sqft_query          = request.args.get('sqft_query')
    heatpump_query      = request.args.get('heatpump_query')

    electric_bill_query = float(electric_bill_query) if electric_bill_query is not None else None
    sqft_query          = float(sqft_query) if sqft_query is not None else None

    return SavingsModel(zip_query, electric_bill_query, sqft_query, heatpump_query)

if __name__ == '__main__':
    app.run(debug=True)