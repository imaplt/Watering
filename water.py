import os
import time
import json
import logging
from datetime import datetime, timedelta
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
        logging.info(f"Priming the pump..")
        pump.on()
        time.sleep(1)
        pump.off()
        logging.info(f"Pump prime complete")
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
            ["rpicam-jpeg", "-c", "camera_config.txt", "-o", image_path],
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
    try:
        # Collect and sort images by modification time (newest first)
        images = sorted(
            [os.path.join(image_directory, f) for f in os.listdir(image_directory) if f.endswith(".jpg")],
            key=os.path.getmtime,
            reverse=True  # Newest files first
        )

        # Select the last N images based on configuration
        image_count = config.get("daily_email_image_count", 6)  # Default to 6
        images_to_send = images[:image_count]  # Take the first N (newest) images

        if not images_to_send:
            logging.info("No images available to send for the daily email.")
            return

        # Send the email with the selected images
        send_email(
            config,
            images_to_send,
            subject="Daily Update: Plant Watering System",
            message="Here are the latest images from the plant watering system."
        )
        logging.info(f"Daily email sent with {len(images_to_send)} images.")
    except Exception as e:
        logging.error(f"Error sending daily email: {e}")


def water_plants(config, state, image_directory):
    now = datetime.now()
    schedule_data = config.get("watering_schedule", [])

    # Ensure state has a dictionary to track last_watered per schedule
    if "last_watered" not in state:
        state["last_watered"] = {}

    for entry in schedule_data:
        start_time = datetime.strptime(entry["start_time"], "%H:%M").time()
        interval_days = entry.get("interval", 1)  # Default to every day
        scheduled_datetime = datetime.combine(now.date(), start_time)

        # Get the last watered time for this specific schedule
        last_watered_datetime = (
            datetime.strptime(state["last_watered"].get(entry["start_time"]), "%Y-%m-%d %H:%M:%S")
            if state["last_watered"].get(entry["start_time"])
            else None
        )

        # Check if the schedule is due based on its interval
        if last_watered_datetime:
            next_valid_day = last_watered_datetime.date() + timedelta(days=interval_days)
            if next_valid_day > now.date():
                continue  # Skip if this schedule is not due yet

        # If the schedule is due and the time has passed
        if scheduled_datetime <= now and (last_watered_datetime is None or scheduled_datetime > last_watered_datetime):
            logging.info(f"Starting watering for schedule: {entry}")
            print(f"Starting watering for schedule: {entry}")
            capture_image(image_directory, f"before_watering_{entry['start_time']}")
            pump.on()
            time.sleep(entry["duration"])
            pump.off()
            capture_image(image_directory, f"after_watering_{entry['start_time']}")

            # Update state for this specific schedule
            state["last_watered"][entry["start_time"]] = scheduled_datetime.strftime("%Y-%m-%d %H:%M:%S")
            save_state(state)
            logging.info(f"Watering completed for schedule: {entry}")
            print(f"Watering completed for schedule: {entry}")

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

    # Check if the last scheduled watering was missed
    now = datetime.now()
    schedule_data = config.get("watering_schedule", [])

    # Get the last schedule up to the current time based on the interval
    latest_scheduled_time = None
    latest_entry = None
    for entry in schedule_data:
        start_time = datetime.strptime(entry["start_time"], "%H:%M").time()
        interval_days = entry.get("interval", 1)  # Default to every day
        scheduled_datetime = datetime.combine(now.date(), start_time)

        # Check if the watering is valid based on the interval
        last_watered_datetime = (
            datetime.strptime(state["last_watered"], "%Y-%m-%d %H:%M:%S")
            if state.get("last_watered")
            else None
        )

        if last_watered_datetime:
            # Calculate the next valid watering day
            next_valid_day = last_watered_datetime.date() + timedelta(days=interval_days)
            if next_valid_day > now.date():
                continue  # Skip if this schedule is not due yet

        # Select the latest schedule up to the current time
        if scheduled_datetime <= now:
            if latest_scheduled_time is None or scheduled_datetime > latest_scheduled_time:
                latest_scheduled_time = scheduled_datetime
                latest_entry = entry

    # Check if the last scheduled time has been watered
    if latest_scheduled_time and latest_entry:
        last_watered_datetime = (
            datetime.strptime(state["last_watered"], "%Y-%m-%d %H:%M:%S")
            if state.get("last_watered")
            else None
        )

        if last_watered_datetime is None or latest_scheduled_time > last_watered_datetime:
            print("Missed watering detected or state file missing. Triggering immediate watering.")
            logging.info("Missed watering detected or state file missing. Triggering immediate watering.")
            capture_image(image_directory, "before_watering")
            pump.on()
            time.sleep(latest_entry["duration"])
            pump.off()
            capture_image(image_directory, "after_watering")

            # Update state with the latest watered time
            state["last_watered"] = latest_scheduled_time.strftime("%Y-%m-%d %H:%M:%S")
            save_state(state)
            logging.info("Immediate watering completed.")

    # Capture startup image and send email (optional)
    startup_image = capture_image(image_directory, "startup")
    # Uncomment to enable email notification
    if startup_image:
        send_email(
            config,
            [startup_image],
            subject="Plant Watering System Started",
            message="The plant watering system has started successfully."
        )
        print("EMail sent...")
        logging.info("Startup EMail sent....")

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
