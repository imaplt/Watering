import threading
import socket
import requests

def verify_flask_server(host="127.0.0.1", port=5000):
    """Checks if a Flask server is running on the specified port."""
    # Check if Flask server thread is running
    flask_thread_detected = any("Thread" in thread.name for thread in threading.enumerate())
    print("Checking for Flask server thread...")
    if flask_thread_detected:
        print("Flask thread detected.")
    else:
        print("No Flask thread detected.")

    # Check if the port is active
    print(f"Checking if port {port} is active...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    port_active = sock.connect_ex((host, port)) == 0
    sock.close()
    if port_active:
        print(f"Port {port} is active.")
    else:
        print(f"Port {port} is not active. Flask server might not be running.")

    # Check if Flask is responding to requests
    if port_active:
        try:
            print("Testing connection to Flask server...")
            response = requests.get(f"http://{host}:{port}")
            if response.status_code == 200:
                print("Flask server is operational and responding to requests.")
            else:
                print(f"Flask server responded with status code {response.status_code}.")
        except requests.ConnectionError:
            print("Flask server is not responding to HTTP requests.")
    else:
        print("Cannot test Flask responsiveness since the port is inactive.")

    # Final status
    if not flask_thread_detected and not port_active:
        print("Flask server does not appear to be running. Please verify your script or environment.")
    elif port_active:
        print(f"Flask server is running on http://{host}:{port}. Try accessing it in your browser.")
    else:
        print("Flask server thread detected but port is not active. Check for potential errors.")

# Run the verification function
verify_flask_server()
