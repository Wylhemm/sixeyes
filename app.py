import csv
import threading
import time
from flask import Flask, render_template, request, session
from instagrapi import Client
import httpx

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with your own secret key

def download_image(url, path):
    with httpx.Client() as client:
        response = client.get(url)
        with open(path, "wb") as file:
            file.write(response.content)

def login(ig_username, ig_password, proxy_ip, proxy_port, proxy_username, proxy_password):
    client = Client()
    client.set_proxy(f"http://{proxy_username}:{proxy_password}@{proxy_ip}:{proxy_port}")
    client.login(ig_username, ig_password)

    if client.two_factor_required:
        return client, True

    return client, False

def send_dm(client, username, message):
    user_id = client.user_id_from_username(username)
    client.direct_send(message, user_ids=[user_id])
    client.direct_send_photo("image.jpg", user_ids=[user_id])

def generate_random_delay(min_delay, max_delay):
    return time.sleep(random.uniform(min_delay, max_delay))

def track_responses(client, sent_messages):
    while True:
        command = input("Enter 'check' to check response rates or 'quit' to exit: ")
        if command == "check":
            total_messages = len(sent_messages)
            responded_messages = 0
            for thread_id in sent_messages:
                thread = client.direct_thread_by_id(thread_id)
                if thread.messages[0].user_id != client.user_id:
                    responded_messages += 1
            response_rate = (responded_messages / total_messages) * 100
            print(f"Response rate: {response_rate}%")
        elif command == "quit":
            break

def read_users_from_csv(file_path):
    users = []
    with open(file_path, "r") as file:
        csv_reader = csv.reader(file)
        for row in csv_reader:
            users.append(row[0])
    return users

def send_messages_from_account(account, users, batch_size):
    ig_username, ig_password, proxy_ip, proxy_port, proxy_username, proxy_password = account
    client, _ = login(ig_username, ig_password, proxy_ip, proxy_port, proxy_username, proxy_password)
    sent_messages = []

    for i in range(0, len(users), batch_size):
        batch_users = users[i:i+batch_size]
        for user in batch_users:
            send_dm(client, user, "Hello! Check out this amazing content.")
            sent_messages.append(client.direct_threads[0].id)
            generate_random_delay(1, 5)

    track_responses(client, sent_messages)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login_route():
    ig_username = request.form["ig_username"]
    ig_password = request.form["ig_password"]
    proxy_ip = request.form["proxy_ip"]
    proxy_port = request.form["proxy_port"]
    proxy_username = request.form["proxy_username"]
    proxy_password = request.form["proxy_password"]

    client, two_factor_required = login(ig_username, ig_password, proxy_ip, proxy_port, proxy_username, proxy_password)

    if two_factor_required:
        session['client'] = client
        return render_template("index.html", two_factor_required=True)
    else:
        return "Login successful!"

@app.route("/two_factor", methods=["POST"])
def two_factor_route():
    two_factor_code = request.form["two_factor_code"]
    client = session.get('client')

    if client:
        client.two_factor_login(two_factor_code)
        return "Two-factor authentication successful!"
    else:
        return "Invalid session", 400

if __name__ == "__main__":
    download_image("https://i.kym-cdn.com/photos/images/original/002/733/202/719.jpg", "image.jpg")

    users = read_users_from_csv("users.csv")
    batch_size = 10

    accounts = [
        ("username1", "password1", "proxy_ip1", "proxy_port1", "proxy_username1", "proxy_password1"),
        ("username2", "password2", "proxy_ip2", "proxy_port2", "proxy_username2", "proxy_password2"),
        # Add more accounts as needed
    ]

    threads = []
    for account in accounts:
        thread = threading.Thread(target=send_messages_from_account, args=(account, users, batch_size))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    app.run()