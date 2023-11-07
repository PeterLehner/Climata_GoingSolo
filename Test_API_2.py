from flask import Flask, request, jsonify


app = Flask(__name__)

@app.route('/add', methods=['POST'])
def add_numbers():
    data = request.get_json()
    if 'number1' not in data or 'number2' not in data:
        return jsonify({'error': 'Please provide both number1 and number2'}), 400
    try:
        number1 = float(data['number1'])
        number2 = float(data['number2'])
    except ValueError:
        return jsonify({'error': 'Please provide valid numbers'}), 400
    return jsonify({'result': number1 + number2})

if __name__ == '__main__':
    app.run(debug=True)
