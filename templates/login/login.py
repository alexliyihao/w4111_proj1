from flask import *

app = Flask(__name__)

@app.route('/error')
def error():
    return "<p><strong>Enter correct password</strong></p>"

@app.route('/')
def login():
    return render_template("login.html")

@app.route('/success',methods = ['POST'])
def success():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['pass']
        login_result = engine.execute("""SELECT dep_id, dep_name FROM department
WHERE username = """ + username + " AND password = " + password +";")

    if login_result.return_rows:
        record = login_result.fetchone()
        resp = make_response(render_template('success.html'))

        resp.set_cookie('dep_id',record["dep_id"])
        resp.set_cookie('dep_name',record["dep_name"])
        #looks like you need did = request.cookies.get('dep_id') to get it
        #it might be a good idea to have a success page then a profile page?
        #let our main page called profile I guess?
        return resp
    else:
        return redirect(url_for('error'))

@app.route('/viewprofile')
def profile():
    dep_id = request.cookies.get('dep_id')
    dep_name = request.cookies.get('dep_name')
    resp = make_response(render_template('profile.html',id = dep_id, name = dep_name))
    return resp

if __name__ == "__main__":
    app.run(debug = True)
