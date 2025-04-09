from flask import Flask, request, jsonify
import sys
import os
from pathlib import Path
from flask_cors import CORS  # Import CORS
from run import run
import json
import base64
import traceback
from board import Board
import datetime

# Add the parent directory to the Python path if needed
sys.path.append(str(Path(__file__).parent))

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Could be anything really, necessary for reading, the file writtien within the request cycle
file_number = 9999

def update_progress(board: Board):
    all = board.sockets.get_socket_count()
    connected = board.connected_sockets_count
    progress = round(float(connected) / float(all), 4) * 100
    print(f"🔵 Updating progress: {progress}")
    # Write the progress to a file
    with open("./progress.txt", 'w') as file:
        file.write(str(progress))

# @app.route('/download_zip', methods=['POST'])
# def download_zip():
#     pass

@app.route('/progress', methods=['GET'])
def get_progress():
    with open("./progress.txt", 'r') as file:
        progress = file.read()
    print(f"🔵 Getting progress: {progress}")
    millis = datetime.datetime.now().timestamp()
    return jsonify({"progress": progress, "timestamp": millis})

@app.route('/run', methods=['POST'])
def begin_routing():

    # Check if the request contains JSON data
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
 
    try:
        # Get the data from the request
        data = request.get_json()
        
        # If data is already a dictionary, convert it back to JSON string to save
        if isinstance(data, dict):
            json_str = json.dumps(data)
        else:
            json_str = data
            
        # Save the data to a file
        with open(f"./data/data_{file_number}.json", 'w') as file:
            file.write(json_str)
        

        # Execute the run function with the provided data
        failed = run(file_number=file_number, run_from_server=True)

        if failed:
            # Clear progress
            with open("./progress.txt", 'w') as file:
                file.write(str(0))

            return jsonify({"error": "Routing failed, try repositioning the modules or increased in the board size."}), 500
        
        # Change the result to return the zip file data
        if os.path.exists("./output.zip"):
            with open("./progress.txt", 'w') as file:
                file.write(str(100))

            with open("./output.zip", 'rb') as zip_file:
                zip_data = zip_file.read()
            # Convert binary data to base64 for safe JSON transmission
            encoded_zip = base64.b64encode(zip_data).decode('utf-8')
            result = {"zipData": encoded_zip, "filename": "output.zip"}
            print('sent output.zip')

        else:
            result = {"message": "Processing completed, but no output.zip was generated"}
            print("failed to send output.zip")
        # Return the result
        return jsonify({"success": True, "result": result})     
    
    except Exception as e:
        
        error_traceback = traceback.format_exc()
        print("Error: An error occurred while processing the request:")
        print(error_traceback)
        return jsonify({"error": str(e), "traceback": error_traceback}), 500

if __name__ == '__main__':
    # Default to port 5000 or use environment variable if specified
    port = int(os.environ.get("PORT", 3333))

    # Clear progress
    with open("./progress.txt", 'w') as file:
        file.write(str(0))

    # Run the Flask app, enabling debug mode for development
    app.run(host='0.0.0.0', port=port, debug=True)
