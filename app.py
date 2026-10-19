from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def root():
    return render_template('index.html')

@app.route('/auth/login')
def login():
    return render_template('auth/login.html')

@app.route('/auth/signup')
def signup():
    return render_template('auth/signup.html')

if __name__ == '__main__':
    app.run(debug=True)
