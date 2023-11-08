from flask import Flask, request, jsonify
import pandas as pd

app = Flask(__name__)

@app.route('/', methods=['GET'])

def ShowZipCodes():
    df_working = pd.read_csv('Data/Zips/zip_lat_lon_state_small.csv')

    df_working['zip'] = [str(x).zfill(5) for x in df_working['zip']] # Make all zips string and 5 characters
   
    return(df_working)

if __name__ == '__main__':
    app.run(debug=True)