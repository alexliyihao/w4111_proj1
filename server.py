#!/usr/bin/env python2.7

"""
Columbia's COMS W4111.001 Introduction to Databases
Example Webserver

To run locally:

    python server.py

Go to http://localhost:8111 in your browser.

A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

import os
import json
from sqlalchemy import *
from datetime import date
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, jsonify, make_response

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)


#
# The following is a dummy URI that does not connect to a valid database. You will need to modify it to connect to your Part 2 database in order to use the data.
#
# XXX: The URI should be in the format of:
#
#     postgresql://USER:PASSWORD@104.196.18.7/w4111
#
# For example, if you had username biliris and password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://biliris:foobar@104.196.18.7/w4111"
#
DATABASEURI = "postgresql://jy3016:<jiayin>@34.74.165.156/proj1part2"


#
# This line creates a database engine that knows how to connect to the URI above.
#
engine = create_engine(DATABASEURI)

#
# Example of running queries in your database
# Note that this will probably not work if you already have a table named 'test' in your database, containing meaningful data. This is only an example showing you how to run queries in your database using SQLAlchemy.
#
engine.execute("""CREATE TABLE IF NOT EXISTS test (
  id serial,
  name text
);""")
engine.execute("""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');""")


@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request.

  The variable g is globally accessible.
  """
  try:
    g.conn = engine.connect()
  except:
    print "uh oh, problem connecting to database"
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't, the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to, for example, localhost:8111/foobar/ with POST or GET then you could use:
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
#
# see for routing: http://flask.pocoo.org/docs/0.10/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#


@app.route('/')
def login():
    return render_template("login.html")

@app.route('/success',methods = ['POST'])
def success():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['pass']
        login_result = engine.execute("SELECT dep_id, dep_name FROM departments WHERE username = '" + username + "' AND password = '" + password +"';")

    for result in login_result.fetchall():
        print "login", result
        idd = result[0]
        dep_name = result[1]
        record = login_result.fetchone()

        resp = make_response(render_template('success.html'))
        resp.set_cookie('dep_id',str(idd))
        resp.set_cookie('dep_name',dep_name)
        return resp
    return redirect("/")


@app.route('/profile')
def index():
  """
  request is a special object that Flask provides to access web request information:

  request.method:   "GET" or "POST"
  request.form:     if the browser submitted a form, this contains the data in the form
  request.args:     dictionary of URL arguments, e.g., {a:1, b:2} for http://localhost?a=1&b=2

  See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
  """

  # DEBUG: this is debugging code to see what request looks like

  dep_id = request.cookies.get('dep_id')
  dep_name = request.cookies.get('dep_name')

  s1 = text(
    "SELECT invoice_id, date as date "
    "FROM invoices "
    "WHERE dept_id = :m "
    "ORDER BY date DESC, invoice_id DESC"
  )

  cursor = g.conn.execute(s1, m = dep_id)
  invoice_id = []
  time = []
  for result in cursor:
    invoice_id.append(result)
    time.append(result['date'])
  cursor.close()

  newlist_time = []
  for item in time:
    newlist_time.append([item.year, item.month, item.day])

  s = text (
    "WITH invoice_id_list AS "
    "(SELECT invoice_id "
    "FROM invoices "
    "WHERE dept_id = :m "
    "), "
    "item_history AS( "
    "SELECT item_category_id, price_at, quantity "
    "FROM invoices_items "
    "WHERE invoice_id IN (SELECT * FROM invoice_id_list) "
    ") "
    "SELECT item_name, C.item_category_id, SUM(Quantity * price_at) "
    "FROM item_category C JOIN item_history H ON C.item_category_id = H.item_category_id "
    "GROUP BY C.item_category_id")

  cursor = g.conn.execute(s, m = dep_id)
  item1 = []
  price1 = []
  item_category_id = []
  for result in cursor:
    item_category_id.append(result['item_category_id'])
    item1.append(str(result['item_name']))
    price1.append(result['sum'])
  cursor.close()

  news = text("WITH invoices_id_list AS ( "
    "SELECT invoice_id "
    "FROM invoices "
    "WHERE dept_id = :m "
    "), "
    "date_cost AS "
    "( SELECT date, sum(price_at*quantity) "
    "FROM invoices_items T JOIN invoices I ON T.invoice_id = I.invoice_id "
    "WHERE T.invoice_id IN (SELECT * FROM invoices_id_list) "
    "GROUP BY date "
    "ORDER BY date DESC "
    ") "
    "SELECT dc1.date, dc1.sum, SUM(dc2.sum) AS total_sum "
    "FROM date_cost dc1 JOIN date_cost dc2 ON dc1.date >= dc2.date "
    "GROUP BY dc1.date, dc1.sum "
    "ORDER BY dc1.date DESC")
  x = []
  price_total = []
  cursor = g.conn.execute(news, m = dep_id)
  for result in cursor:
    x.append(result['date'])  # can also be accessed using result[0]
    price_total.append(result['total_sum'])
  cursor.close()

  newlist_total = [[item.year, item.month, item.day] for item in x]

  s = text(
        "SELECT date, price_at "
        "FROM invoices_items T JOIN invoices I ON T.invoice_id = I.invoice_id "
        "WHERE dept_id = :m AND item_category_id = :x "
        "ORDER BY date DESC"
      )
  timelist = []
  pricelist = []
  idlist = []

  for item in item_category_id:
    price = []
    x = []
    idlist.append(item_category_id)
    cursor = g.conn.execute(s, x = item, m = dep_id)
    for result in cursor:
        x.append(result['date'])  # can also be accessed using result[0]
        price.append(result['price_at'])
    cursor.close()

    newlist = [[item.year, item.month, item.day] for item in x]
    timelist.append(newlist)
    pricelist.append(price)
  print timelist
  print pricelist

  s = text(
    "WITH invoice_id_list AS "
    "(SELECT invoice_id "
    "FROM invoices "
    "WHERE dept_id = :m) "
    "SELECT SUM(Balance) "
    "FROM (SELECT SUM(Quantity * price_at) AS Balance "
    "FROM item_category C JOIN invoices_items I ON C.item_category_id = I.item_category_id "
    "Where invoice_id IN (SELECT * FROM invoice_id_list)) fd"
  )
  cursor = g.conn.execute(s, m = dep_id)
  for result in cursor:
      sum = result[0]
  cursor.close()

  context = dict(dep_name = dep_name,
                 idlist = idlist,
                 timelist = timelist,
                 pricelist = pricelist,
                 sum = sum,
                 invoice_id = invoice_id,
                 time = newlist_time,
                 item_category_id = item_category_id,
                 data = price_total,
                 data1 = newlist_total,
                 item = item1,
                 price = price1)
  #
  # render_template looks in the templates/ folder for files.
  # for example, the below file reads template/index.html
  #
  print "Into profile"
  return make_response(render_template("index2.html", **context))

@app.route('/profile/transaction', methods = ['POST', 'GET'])
def transaction():
  s1 = text("SELECT item_name from item_category")
  categorytype = []

  cursor = g.conn.execute(s1)
  for result in cursor:
    categorytype.append(result['item_name'])
  cursor.close()

  print categorytype

  print "Into supplier search"
  return render_template("transaction.html", type = categorytype)

@app.route('/profile/<id>',methods = ['POST', 'GET'])
def another(id):

    s1 = text(
      """SELECT SUM(Quantity * price_at) AS Balance
         FROM item_category C JOIN invoices_items I ON C.item_category_id = I.item_category_id
         Where invoice_id = :y"""
    )
    cursor = g.conn.execute(s1, y = id)
    for result in cursor:
      balance = result[0]
    cursor.close()

    s = text(
      "SELECT C.item_category_id AS item_id, "
      "item_name, price_at AS price, "
      "quantity, "
      "from_supplier_id AS supplier_id "
      "FROM item_category C JOIN invoices_items I ON C.item_category_id = I.item_category_id "
      "Where Invoice_ID = :x"
    )
    listres = []
    cursor = g.conn.execute(s, x = id)
    for result in cursor:
      listres.append(result)
    cursor.close()

    print "check invoice ", id
    return render_template("another.html", result = listres, total = balance)

@app.route('/profile/about/')
def about():
  return redirect('/profile')

@app.route('/profile/contact')
def contact():
  return render_template("contact.html")

@app.route('/profile/addabout')
def addabout():
  return redirect('/profile/')

@app.route('/profile/addnew', methods = ['POST', 'GET'])
def addnew():
  cursor = g.conn.execute("select item_category_id, item_name from item_category");
  listres = []
  for result in cursor:
      listres.append(result['item_name'])
  cursor.close()
  print "adding new invoice page #1"
  resp = make_response(render_template('add.html', AllCategory = listres))
  resp.delete_cookie("cat_id")
  resp.delete_cookie("sup_id")
  resp.delete_cookie("add_id")
  return resp


# Example of adding new data to the database
@app.route('/profile/ConfirmCategory/', methods=['POST'])
def ConfirmCategory():

  if request.form.get('selectCate') == None:
    return redirect("/profile/addnew")

  idd = str(request.form.get('selectCate'))

  s = text("select item_category_id from item_category where item_name = :x")
  cursor = g.conn.execute(s, x = idd);
  for result in cursor:
      idd = result[0]
  cursor.close()
  print "item Category id:" , idd

  listres = []

  s = text(
    """SELECT I.supplier_id, supplier_name
    FROM supplier_item I join suppliers S ON I.supplier_id = S.supplier_id
    WHERE item_category_id = :idd"""
  )
  item = []
  suppname = []
  cursor = g.conn.execute(s, idd = idd)
  for result in cursor:
    suppname.append(result['supplier_name'])
    item.append(result['supplier_id'])
  cursor.close()

  info = {"item": item}
  resp = make_response(render_template('add.html', data = suppname))
  resp.set_cookie('cat_id',str(idd))
  print "adding new invoice page #2"
  return resp

@app.route('/profile/ConfirmSupplier/', methods=['POST'])
def ConfirmSupplier():
  iid = str(request.form.get('select'))
  print "supplier_name", iid
  if request.form.get('select') == None:
    return redirect("/profile/addnew")

  s = text("SELECT supplier_id from suppliers WHERE supplier_name = :id")
  cursor = g.conn.execute(s, id = iid)
  for result in cursor:
    iid = result[0]
  cursor.close()

  s = text(
    "SELECT address_id, address_string FROM addresses WHERE supplier_id = :iid"
  )
  idd = []
  adstring = []
  cursor = g.conn.execute(s, iid = iid)
  for result in cursor:
    idd.append(result['address_id'])
    adstring.append(result['address_string'])
  cursor.close()

  resp = make_response(render_template('add.html', name = adstring, id = idd))
  resp.set_cookie('sup_id',str(iid))
  print "adding new invoice page #3"
  return resp

@app.route('/profile/ConfirmAdd/', methods=['POST'])
def ConfirmAdd():

  if request.form.get('selectadd') == None:
    return redirect("/profile/addnew")

  iid = str(request.form.get('selectadd'))
  print "address_id", iid

  s = text("SELECT address_id FROM addresses WHERE address_string = :iid")
  cursor = g.conn.execute(s, iid = iid);
  for res in cursor:
    iid = res[0]
  cursor.close()

  resp = make_response(render_template('add.html'))
  resp.set_cookie('add_id',str(iid))
  print "adding new invoice page #4"
  return resp

@app.route('/profile/load/', methods=['POST'])
def load():

  Category = str(request.cookies.get('cat_id'))
  print "Category_id", Category
  Supplier = str(request.cookies.get('sup_id'))
  print "Supplier_id", Supplier
  Address = str(request.cookies.get('add_id'))
  print "address_id", Address

  dep = request.cookies.get('dep_id')

  Price = request.form['Price']
  print "Price", Price
  Quantity = request.form['Quantity']
  print "Quantity", Quantity

  s = text("select max(invoice_id) from invoices")
  maxnum = -1;
  cursor = g.conn.execute(s)
  for result in cursor:
    maxnum = result[0] + 1
  cursor.close()
  print "invoice_number", maxnum

  if Category != "None" and Supplier != "None" and Address != "None" and Price.replace(".","1").isnumeric() and Quantity.isnumeric():
    print "after check:------"
    Category = int(Category)
    print "Category_id", Category
    Supplier = int(Supplier)
    print "Supplier_id", Supplier
    Address = int(Address)
    print "address_id", Address
    Price = round(float(Price),2)
    print "Price", Price
    Quantity = int(Quantity)
    print "Quantity", Quantity

    if Category >= 1 and Category <= 10 and Supplier >= 0 and Supplier <= 9 and Address >= 1 and Address <= 13:
      print ("valid value")
      today = date.today()
      s2 = text("insert into invoices values(:maxnum, :today, :dep)")
      g.conn.execute(s2, maxnum = maxnum, today = today, dep = dep)
      s1 = text("insert into invoices_items values(:maxnum, :Category, :Supplier, :Address, :Price, :Quantity)")
      g.conn.execute(s1,maxnum = maxnum,Category =Category, Supplier = Supplier, Address = Address, Price = Price, Quantity = Quantity)

      print "invoice added"
      return redirect("/profile")

  return redirect("/profile/addnew")


@app.route('/profile/add', methods=['POST'])
def add():
  name = str(request.form.get('select'))

  #name = request.form['name']
  print name
  if request.form.get('select') == None:
    print name
    return redirect('/profile/transaction')

  s = text("SELECT item_category_id from item_category WHERE item_name = :x")
  cursor = g.conn.execute(s,x = name).fetchall()
  for result in cursor:
    name = result[0]

  s = text(
  "WITH supplier_id_list AS "
  "(SELECT supplier_id "
  "FROM supplier_item "
  "WHERE item_category_id = :z) "
  "SELECT S.supplier_id, S.supplier_name, A.address_string, A.zip_code "
  "FROM suppliers S JOIN addresses A ON S.supplier_id = A.supplier_id "
  "WHERE S.supplier_id IN (SELECT * FROM supplier_id_list) "
  )

  cursor = g.conn.execute(s,z = name)
  results = []
  for result in cursor:
    results.append(result)
  cursor.close()

  s = text("SELECT item_name from item_category")
  cursor = g.conn.execute(s)
  categorytype = []
  for result in cursor:
    categorytype.append(result['item_name'])
  cursor.close()

  print categorytype
  #g.conn.execute('INSERT INTO test VALUES (NULL, ?)', name)
  return render_template("transaction.html", result = results, type = categorytype)


if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using:

        python server.py

    Show the help text using:

        python server.py --help

    """

    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.run(host=HOST, port=PORT, debug=True, threaded=threaded)


  run()
