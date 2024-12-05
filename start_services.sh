#!/bin/bash

# Start the watering script
echo "Starting watering script..."
python3 /home/imaplt/watering/watering/water.py &

# Start the Flask application
echo "Starting Flask application..."
python3 /home/imaplt/watering/watering/web_app.py &

echo "Services started."
