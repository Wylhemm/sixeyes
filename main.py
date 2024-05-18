import os
import time
import random
import requests
import httpx
import csv
import threading
from flask import Flask, request, render_template_string
from instagrapi import Client
from instagrapi.exceptions import TwoFactorRequired, ClientError

# Define the range for the delay in seconds
MIN_DELAY = 15
MAX_DELAY = 20

# URL of the image to send
IMAGE_URL = "https://i.kym-cdn.com/photos/images/original/002/733/202/719.jpg"
IMAGE_PATH = "downloaded_image.jpg"

# Define the global messages for split testing
GLOBAL_MESSAGES = [
    "Shockingly shameful to start any convo this way but if I could get you 30 gym members in the door within 1 month & you’d only pay per signed member without wasting time studying marketing, would you be interested in a partnership?",
    "If I could get you 30 gym members in the door within 1 month & you’d only pay per signed member without wasting time studying marketing, would you be interested in a partnership?"
]

# List of accounts and proxies
ACCOUNTS = [
    {
        "ig_username": "sanazpiramun22",
        "ig_password": "horoz123",
        "proxy_ip": "portal.anyip.io",
        "proxy_port": "1080",
        "proxy_username": "user_42079f,type_mobile,country_US,lat_40.417287,lon_-82.907123,asn_21928,session_randSession1170",
        "proxy_password": "739fe7"
    }
]

# Flask app to handle 2FA input
app = Flask(__name__)
two_factor_code = None

@app.route('/', methods=['GET', 'POST'])
def index():
    global two_factor_code
    if request.method == 'POST':
        two_factor_code = request.form['2fa_code']
        return '2FA code received'
    return render_template_string('''
        <form method="post">
            2FA Code: <input type="text" name="2fa_code">
            <input type="submit" value="Submit">
        </form>
    ''')

@app.route('/get_2fa_code', methods=['GET'])
def get_2fa_code():
    global two_factor_code
    return two_factor_code if two_factor_code else '', 200

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

def download_image(url, path):
    with httpx.Client() as client:
        response = client.get(url)
        if response.status_code == 200:
            with open(path, 'wb') as file:
                file.write(response.content)
            print(f"Image downloaded to {path}")
        else:
            print(f"Failed to download image from {url}")

def login(ig_username, ig_password, proxy_ip, proxy_port, proxy_username, proxy_password):
    client = Client()
    proxy = f"http://{proxy_username}:{proxy_password}@{proxy_ip}:{proxy_port}"
    client.set_proxy(proxy)
    try:
        client.login(ig_username, ig_password)
        return client
    except TwoFactorRequired as e:
        print(f"Two-factor authentication required for {ig_username}.")
        while True:
            response = requests.get('http://localhost:5000/get_2fa_code')
            if response.status_code == 200 and response.text:
                two_factor_code = response.text
                break
            time.sleep(5)
        client.two_factor_login(ig_username, ig_password, two_factor_code)
        return client
    except Exception as e:
        print(f"Login failed for {ig_username}: {e}")
        return None

def send_dm(client, username, message):
    try:
        user_id = client.user_id_from_username(username)

        # Send the message
        dm_id = client.direct_send(message, [user_id])
        print(f"Message sent to {username} with ID: {dm_id}")

        # Send the photo
        photo_dm_id = client.direct_send_photo(IMAGE_PATH, [user_id])
        print(f"Photo sent to {username} with ID: {photo_dm_id}")

        return {'thread_id': dm_id.thread_id, 'message_type': message}

    except ClientError as e:
        print(f"Failed to send DM to {username}: {e}")
        return None

def generate_random_delay(min_delay, max_delay):
    mean = (min_delay + max_delay) / 2
    std_dev = (max_delay - min_delay) / 6  # 99.7% of values will be within the range
    delay = random.gauss(mean, std_dev)
    return max(min_delay, min(max_delay, delay))

def track_responses(client, sent_messages):
    while True:
        command = input("Enter 'check' to check response rates or 'quit' to exit: ")
        if command.lower() == 'check':
            total_messages = len(sent_messages)
            responded_messages = {}
            for message_type in GLOBAL_MESSAGES:
                responded_messages[message_type] = 0

            for dm_info in sent_messages:
                thread_id = dm_info['thread_id']
                message_type = dm_info['message_type']
                try:
                    thread = client.direct_threads(thread_id)
                    if thread and thread[0].messages:
                        last_message = thread[0].messages[-1]
                        if last_message.user_id != client.user_id:
                            responded_messages[message_type] += 1
                except ClientError as e:
                    print(f"Error retrieving thread {thread_id}: {e}")
                    continue  # Skip to the next thread if an error occurs

            print("Response Rates:")
            for message_type, count in responded_messages.items():
                total_messages_of_type = sum(1 for dm_info in sent_messages if dm_info['message_type'] == message_type)
                response_rate = (count / total_messages_of_type) * 100 if total_messages_of_type > 0 else 0
                print(f"{message_type}: {response_rate:.2f}%")

        elif command.lower() == 'quit':
            break
        else:
            print("Invalid command. Please try again.")

def read_users_from_csv(file_path):
    users = []
    with open(file_path, newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if row:  # Ensure the row is not empty
                users.append(row[0].strip())
    return users

def send_messages_from_account(account, users, batch_size):
    client = login(
        account['ig_username'],
        account['ig_password'],
        account['proxy_ip'],
        account['proxy_port'],
        account['proxy_username'],
        account['proxy_password']
    )
    if not client:
        return

    sent_messages = []
    for i in range(0, len(users), batch_size):
        batch = users[i:i + batch_size]
        for user in batch:
            message = random.choice(GLOBAL_MESSAGES)
            dm_info = send_dm(client, user, message)
            if dm_info:
                sent_messages.append(dm_info)
            # Generate a random delay within the specified range
            delay = generate_random_delay(MIN_DELAY, MAX_DELAY)
            print(f"Waiting for {delay:.2f} seconds before sending the next message...")
            time.sleep(delay)

    track_responses(client, sent_messages)

if __name__ == "__main__":
    # Start the Flask app in a separate thread
    threading.Thread(target=run_flask).start()

    # Download the image before sending DMs
    download_image(IMAGE_URL, IMAGE_PATH)

    # Read Instagram usernames from CSV file
    users_to_message = read_users_from_csv('users.csv')

    # Customize the batch size
    BATCH_SIZE = 10

    # Split users into batches and assign to accounts
    threads = []
    for account in ACCOUNTS:
        thread = threading.Thread(target=send_messages_from_account, args=(account, users_to_message, BATCH_SIZE))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()
