import os
import time
import json
import logging
from datetime import datetime
from gpiozero import OutputDevice
from smtplib import SMTP_SSL
from email.message import EmailMessage
import schedule
import subprocess

# Configure logging
logging.basicConfig(
    filename="/mnt/data/system.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Load configuration
def load_config(config_path="config.json"):
    try:
        with open(config_path, "r") as file:
            return json.load(file)
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        return {}

# Save state (last watering time)
def save_state(state, state_file="state.json"):
    try:
        with open(state_file, "w") as file:
            json.dump(state, file)
        logging.info(f"State saved: {state}")
    except Exception as e:
        logging.error(f"Error saving state: {e}")

# Load state
def load_state(state_file="state.json"):
    if os.path.exists(state_file):
        try:
            with open(state_file, "r") as file:
                return json.load(file)
        except Exception as e:
            logging.error(f"Error loading state: {e}")
    return {"last_watered": None}

# Initialize pump
pump = None

def initialize_pump(pin):
    global pump
    try:
        pump = OutputDevice(pin, active_high=False)
        logging.info(f"Pump initialized on GPIO pin {pin}")
    except Exception as e:
        logging.error(f"Error initializing pump: {e}")

# Capture image using rpicam
def capture_image(image_directory, label):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    image_name = f"{label}_{timestamp}.jpg"
    image_path = os.path.join(image_directory, image_name)

    # Ensure the directory exists
    os.makedirs(image_directory, exist_ok=True)

    try:
        subprocess.run(
            ["rpicam-jpeg", "-c camera_config.txt", "-o", image_path],
            check=True
        )
        logging.info(f"Image captured: {image_path}")
        return image_path
    except subprocess.CalledProcessError as e:
        logging.error(f"Error capturing image: {e}")
        return None

# Send email
def send_email(config, images, subject, message):
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = config["email"]["sender_email"]
        msg["To"] = config["email"]["recipient_email"]
        msg.set_content(message)

        for image in images:
            with open(image, "rb") as img_file:
                img_data = img_file.read()
                msg.add_attachment(img_data, maintype="image", subtype="jpeg", filename=os.path.basename(image))

        with SMTP_SSL(config["email"]["smtp_server"], config["email"]["smtp_port"]) as smtp:
            smtp.login(config["email"]["sender_email"], config["email"]["password"])
            smtp.send_message(msg)
            logging.info(f"Email sent successfully: {subject}")
    except Exception as e:
        logging.error(f"Error sending email: {e}")

# Capture periodic images
def periodic_image_capture(config, image_directory):
    capture_image(image_directory, "periodic")

# Send daily email with recent images
def send_daily_email(config, image_directory):
    images = sorted(
        [os.path.join(image_directory, f) for f in os.listdir(image_directory) if f.endswith(".jpg")],
        key=os.path.getmtime
    )[-config.get("daily_email_image_count", 6):]  # Last N images

    if images:
        send_email(
            config,
            images,
            subject="Daily Update: Plant Watering System",
            message="Here are the latest images from the plant watering system."
        )

# Water plants
def water_plants(config, state, image_directory):
    now = datetime.now()
    schedule_data = config.get("watering_schedule", [])

    for entry in schedule_data:
        start_time = datetime.strptime(entry["start_time"], "%H:%M").time()
        duration = entry["duration"]

        if now.time() >= start_time and state["last_watered"] != entry["start_time"]:
            logging.info(f"Starting watering for schedule: {entry}")
            capture_image(image_directory, "before_watering")
            pump.on()
            time.sleep(duration / 2)
            capture_image(image_directory, "halfway_watering")
            time.sleep(duration / 2)
            pump.off()
            capture_image(image_directory, "after_watering")
            state["last_watered"] = entry["start_time"]
            save_state(state)
            logging.info(f"Watering completed for schedule: {entry}")

# Scheduler tasks
def setup_schedule(config, state, image_directory):
    # Image capture every `image_capture_interval` seconds
    interval = config.get("image_capture_interval", 1800)  # Default to 30 minutes
    schedule.every(interval).seconds.do(periodic_image_capture, config, image_directory)

    # Daily email at configured time
    daily_time = config.get("daily_email_time", "09:00")
    schedule.every().day.at(daily_time).do(send_daily_email, config, image_directory)

    # Watering schedule
    for entry in config.get("watering_schedule", []):
        schedule.every().day.at(entry["start_time"]).do(water_plants, config, state, image_directory)

# Main function
def main():
    config = load_config()
    state = load_state()
    image_directory = config.get("image_directory", "images")
    os.makedirs(image_directory, exist_ok=True)
    logging.info("System initialized.")

    initialize_pump(config["relay_pin"])

    # Capture startup image and send email
    startup_image = capture_image(image_directory, "startup")
    if startup_image:
        send_email(
            config,
            [startup_image],
            subject="Plant Watering System Started",
            message="The plant watering system has started successfully."
        )

    # Set up the schedule
    setup_schedule(config, state, image_directory)

    logging.info("System running. Press Ctrl+C to stop.")
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)  # Prevent CPU overuse
    except KeyboardInterrupt:
        logging.info("Shutting down.")
        if pump:
            pump.off()

# Uncomment to run
if __name__ == "__main__":
    main()
