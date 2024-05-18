from flask import Flask, request, render_template_string
import threading

app = Flask(__name__)

# Global variable to store the 2FA code
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

def run_flask():
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
