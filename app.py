from flask import Flask, render_template, request
from instagrapi import Client
import csv
import time

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        message = request.form['message']
        
        cl = Client()
        cl.login(username, password)

        with open('users.csv', 'r') as file:
            reader = csv.reader(file)
            for row in reader:
                user_id = cl.user_id_from_username(row[0])
                cl.direct_send(message, [user_id])
                time.sleep(30)

        return "Messages sent successfully!"

    return render_template('index.html')

if __name__ == '__main__':
    app.run()
