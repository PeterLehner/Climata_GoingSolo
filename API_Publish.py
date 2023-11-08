from flask import *
import json, time
from API_Main import *

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home_page():
    data_set = {'Page': 'Home', 'Message': 'Successfully loaded the Home page', 'Timestamp': time.time()}
    json_dump = json.dumps(data_set)

    zip_query = '02340'
    electric_bill_query = 125
    heatpump_query = True

    net_savings_for_API, heatpump_savings, total_upfront_incentives = main(zip_query, heatpump_query, electric_bill_query)

    data_set = {'Net savings': f'{net_savings_for_API}', 'heatpump savings': f'{heatpump_savings}', 'Incentives': f'{total_upfront_incentives}', 'Timestamp': time.time()}
    
    json_dump = json.dumps(data_set)
    
    return json_dump

@app.route('/data/', methods= ['GET'])
def request_page():
    zip_query = str(request.args.get('zip')) # /user/?zip=zip_code
    electric_bill_query = int(request.args.get('bill')) # /user/?bill=125
    heatpump_query = str(request.args.get('heatpump')) # /user/?zip=zip_code
    if heatpump_query == 'True':
        heatpump_query = True
    else:
        heatpump_query = False

    net_savings_for_API, heatpump_savings, total_upfront_incentives = main(zip_query, heatpump_query, electric_bill_query)

    data_set = {'Net savings': f'{net_savings_for_API}', 'heatpump savings': f'{heatpump_savings}', 'Incentives': f'{total_upfront_incentives}', 'Timestamp': time.time()}
    json_dump = json.dumps(data_set)

    return json_dump

if __name__ == '__main__':
    app.run(port=8888)