from flask import Flask, render_template_string, send_from_directory, escape
import os
from datetime import datetime
import logging

app = Flask(__name__)

# Directory where images are stored
image_directory = "/mnt/data/test_images"
log_file_path = "/mnt/data/system.log"

# HTML template for the index page
flask_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Plant Watering System</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f4f4f9;
        }
        h1 {
            text-align: center;
            padding: 20px;
            color: #333;
        }
        .gallery {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 10px;
            padding: 20px;
        }
        .gallery img {
            max-width: 200px;
            border: 2px solid #ccc;
            border-radius: 8px;
            transition: transform 0.2s;
        }
        .gallery img:hover {
            transform: scale(1.1);
            border-color: #777;
        }
        .footer {
            text-align: center;
            padding: 10px;
            background-color: #333;
            color: white;
            margin-top: 20px;
        }
        .nav {
            text-align: center;
            margin-bottom: 20px;
        }
        .nav a {
            text-decoration: none;
            margin: 0 15px;
            font-size: 18px;
            color: #007BFF;
        }
        .nav a:hover {
            text-decoration: underline;
        }
        pre {
            background-color: #f8f9fa;
            padding: 20px;
            border: 1px solid #ccc;
            border-radius: 8px;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
    </style>
</head>
<body>
    <h1>Plant Watering System</h1>
    <div class="nav">
        <a href="/">Home</a>
        <a href="/logs">View Logs</a>
    </div>
    <div class="gallery">
        {% for image in images %}
        <a href="/images/{{ image }}" target="_blank">
            <img src="/images/{{ image }}" alt="{{ image }}">
        </a>
        {% endfor %}
    </div>
    <div class="footer">
        &copy; {{ year }} Raspberry Pi Plant System
    </div>
</body>
</html>
"""

@app.route("/")
def index():
    # Get the list of images and their metadata
    images = [
        {
            "filename": f,
            "timestamp": datetime.fromtimestamp(os.path.getmtime(os.path.join(image_directory, f))).strftime("%Y-%m-%d %H:%M:%S")
        }
        for f in os.listdir(image_directory) if f.endswith(".jpg")
    ]

    # Sort images by their modification times (ascending order)
    images.sort(key=lambda x: x["timestamp"])

    # Render the template with the sorted image list and metadata
    return render_template_string(
        """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <title>Plant Watering System</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: #f4f4f9;
                }
                h1 {
                    text-align: center;
                    padding: 20px;
                    color: #333;
                }
                .gallery {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    padding: 20px;
                    justify-items: center;
                }
                .gallery-item {
                    text-align: center;
                }
                .gallery-item img {
                    max-width: 100%;
                    height: auto;
                    border: 2px solid #ccc;
                    border-radius: 8px;
                    transition: transform 0.2s;
                }
                .gallery-item img:hover {
                    transform: scale(1.1);
                    border-color: #777;
                }
                .footer {
                    text-align: center;
                    padding: 10px;
                    background-color: #333;
                    color: white;
                    margin-top: 20px;
                }
                .nav {
                    text-align: center;
                    margin-bottom: 20px;
                }
                .nav a {
                    text-decoration: none;
                    margin: 0 15px;
                    font-size: 18px;
                    color: #007BFF;
                }
                .nav a:hover {
                    text-decoration: underline;
                }
                pre {
                    background-color: #f8f9fa;
                    padding: 20px;
                    border: 1px solid #ccc;
                    border-radius: 8px;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }
            </style>
        </head>
        <body>
            <h1>Plant Watering System</h1>
            <div class="nav">
                <a href="/">Home</a>
                <a href="/logs">View Logs</a>
            </div>
            <div class="gallery">
                {% for image in images %}
                <div class="gallery-item">
                    <a href="/images/{{ image.filename }}" target="_blank">
                        <img src="/images/{{ image.filename }}" alt="{{ image.filename }}">
                    </a>
                    <p>{{ image.timestamp }}</p>
                </div>
                {% endfor %}
            </div>
            <div class="footer">
                &copy; {{ year }} Raspberry Pi Plant System
            </div>
        </body>
        </html>
        """,
        images=images,
        year=datetime.now().year
    )


@app.route("/images/<filename>")
def serve_image_direct(filename):
    file_path = os.path.join(image_directory, filename)
    try:
        if not os.path.exists(file_path):
            logging.error(f"File not found: {file_path}")
            return "File not found", 404
        return send_from_directory(image_directory, filename)
    except Exception as e:
        logging.error(f"Error serving image: {e}")
        return f"Error serving image: {e}", 500

@app.route("/logs")
def view_logs():
    try:
        print(f"Accessing log file at: {log_file_path}")
        with open(log_file_path, "r") as log_file:
            logs = log_file.read()
        # Escape log content to ensure special characters do not break HTML
        logs = escape(logs)
        return render_template_string(
            """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <title>System Logs</title>
            </head>
            <body>
                <h1>System Logs</h1>
                <pre>{{ logs }}</pre>
                <a href="/">Back to Home</a>
            </body>
            </html>
            """,
            logs=logs
        )
    except FileNotFoundError:
        print("Log file not found.")
        return render_template_string(
            """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <title>System Logs</title>
            </head>
            <body>
                <h1>System Logs</h1>
                <p>Log file not found.</p>
                <a href="/">Back to Home</a>
            </body>
            </html>
            """
        )
    except Exception as e:
        print(f"Error reading log file: {e}")
        return render_template_string(
            """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <title>System Logs</title>
            </head>
            <body>
                <h1>System Logs</h1>
                <p>Error: {{ error }}</p>
                <a href="/">Back to Home</a>
            </body>
            </html>
            """,
            error=e
        )

try:
    app.run(host="0.0.0.0", port=5000, debug=True)
except Exception as e:
    print(f"Flask encountered an error: {e}")
