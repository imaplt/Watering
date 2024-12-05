import os
import subprocess

# Directory to fix permissions
image_directory = "/mnt/data/test_images"
log_file = "/mnt/data/service.log"
log_directory = "/mnt/data"
flask_user = "imaplt"  # User running the Flask process


def fix_permissions(directory, user):
    try:
        # Change ownership to the specified user
        print(f"Changing ownership of {directory} to {user}:{user}...")
        subprocess.run(["sudo", "chown", "-R", f"{user}:{user}", directory], check=True)

        # Change permissions to 755 (read/write/execute for owner, read/execute for others)
        print(f"Setting permissions of {directory} to 755...")
        subprocess.run(["sudo", "chmod", "-R", "755", directory], check=True)

        print("Permissions successfully updated.")
    except subprocess.CalledProcessError as e:
        print(f"Error while updating permissions: {e}")

def fix_file_permissions(directory, user):
    try:
        # Change ownership to the specified user
        print(f"Changing file ownership of {directory} to {user}:{user}...")
        subprocess.run(["sudo", "chown", f"{user}:{user}", directory], check=True)

        # Change permissions to 755 (read/write/execute for owner, read/execute for others)
        print(f"Setting file permissions of {directory} to 755...")
        subprocess.run(["sudo", "chmod", "755", directory], check=True)

        print("Permissions successfully updated.")
    except subprocess.CalledProcessError as e:
        print(f"Error while updating permissions: {e}")

if __name__ == "__main__":
    if os.path.exists(image_directory):
        fix_permissions(image_directory, flask_user)
    else:
        print(f"Directory {image_directory} does not exist. Please check the path.")

    if os.path.exists(log_directory):
        fix_permissions(log_directory, flask_user)
    else:
        print(f"Directory {log_directory} does not exist. Please check the path.")

    if os.path.exists(log_file):
       fix_file_permissions(log_file, flask_user)
    else:
        print(f"Directory {log_directory} does not exist. Please check the path.")
