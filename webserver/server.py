#!/usr/bin/env python2.7

"""
Columbia W4111 Intro to databases
Example webserver

To run locally

    python server.py

Go to http://localhost:8111 in your browser


A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, session, url_for, escape, flash

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)



# XXX: The Database URI should be in the format of:
#
#     postgresql://USER:PASSWORD@<IP_OF_POSTGRE_SQL_SERVER>/<DB_NAME>
#
# For example, if you had username ewu2493, password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://ewu2493:foobar@<IP_OF_POSTGRE_SQL_SERVER>/postgres"
#
# For your convenience, we already set it to the class database

# Use the DB credentials you received by e-mail
DB_USER = "aes2329"
DB_PASSWORD = "Cd7hKjmy2J"


DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"

DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/w4111"


#
# This line creates a database engine that knows how to connect to the URI above
#
engine = create_engine(DATABASEURI)


# Here we create a test table and insert some values in it
engine.execute("""DROP TABLE IF EXISTS test;""")
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
  We use it to setup a database connection that can be used throughout the request

  The variable g is globally accessible
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
  If you don't the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to e.g., localhost:8111/foobar/ with POST or GET then you could use
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
#
# see for routing: http://flask.pocoo.org/docs/0.10/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#



@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if 'username' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username_form  = request.form['username']
        password_form  = request.form['password']
        cursor = g.conn.execute("SELECT COUNT(1) FROM app_user WHERE username = %s;", [username_form]) # CHECKS IF USERNAME EXISTS
        if cursor.fetchone()[0]:
            cursor = g.conn.execute("SELECT password FROM app_user WHERE username = %s;", [username_form]) # FETCH THE HASHED PASSWORD
            for row in cursor.fetchall():
                if password_form == row[0]:
                    session['username'] = request.form['username']
                    flash('You were successfully logged in')
                    return redirect(url_for('dashboard'))
                else:
                    error = "Invalid Credential"
        else:
            error = "Invalid Credential"
    return render_template('login.html', error=error)

@app.route('/')
def dashboard():
  """
  request is a special object that Flask provides to access web request information:

  request.method:   "GET" or "POST"
  request.form:     if the browser submitted a form, this contains the data in the form
  request.args:     dictionary of URL arguments e.g., {a:1, b:2} for http://localhost?a=1&b=2

  See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
  """

  # DEBUG: this is debugging code to see what request looks like
  print session


  #
  # example of a database query
  #
  if 'username' in session:
      username_session = escape(session['username']).capitalize()
      cursor = g.conn.execute("SELECT wine_title FROM graded ORDER BY rating DESC LIMIT 5;")
      wine_titles = []
      for result in cursor:
        wine_titles.append(result['wine_title'])  # can also be accessed using result[0]
      cursor.close()

      context = dict(data = wine_titles)
      print context
      return render_template("dashboard.html", **context)
  return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('dashboard'))


@app.route('/another')
def another():
  return render_template("anotherfile.html")

@app.route('/wine',methods = ['GET'])
def wine():
    print request.args
    name = request.args.get('wine_title')
    #Querying the full information from the wine
    cursor1 = g.conn.execute("SELECT wine_title,price,variety,winery_name,username FROM wine WHERE wine_title LIKE %s",('%' + name.encode('utf-8') +'%'))
    for result in cursor1:
        wine_title = result['wine_title']
        price = result['price']
        variety = result['variety']
        winery_name = result['winery_name']
        username = result['username']
    cursor1.close()

    #Querying the grade for this wine
    cursor2 = g.conn.execute("SELECT AVG(rating) AS grade FROM graded WHERE wine_title = %s",wine_title)
    for result in cursor2:
        grade = result['grade']
    cursor2.close()

    tasters = []
    reviews = []
    ratings = []
    #Querying the reviews for this wine
    cursor3 = g.conn.execute("SELECT taster_name, description, rating FROM reviewed WHERE wine_title = %s;",wine_title)
    for result in cursor3:
        tasters.append(result['taster_name'])
        reviews.append(result['description'])
        ratings.append(result['rating'])
    cursor3.close()

    is_in_winelist = False
    cursor4 = g.conn.execute("SELECT COUNT(*) FROM winelist,app_user WHERE wine_title = %s AND app_user.list_id = winelist.list_id AND username = %s;",(name,session['username']))
    for result in cursor4:
        if(result['count'] > 0):
            is_in_winelist  = True
    cursor4.close()

    context = dict()
    context['count'] = is_in_winelist
    print(context)
    context['wine_title'] = wine_title
    context['price'] = price
    context['variety'] = variety
    context['winery_name'] = winery_name
    context['username'] = username
    context['grade'] = "%.1f" % grade
    context['tasters'] = tasters
    context['reviews'] = reviews
    context['ratings'] = ratings
    return render_template("wine.html", **context)


@app.route('/review',methods = ['GET'])
def review():
    wine_title = request.args.get('wine_title')
    taster =  request.args.get('taster')
    #Querying the reviews for this wine
    cursor = g.conn.execute("SELECT description, rating FROM reviewed WHERE wine_title = %s AND taster_name = %s;",(wine_title,taster))
    for result in cursor:
        description = result['description']
        rating = result['rating']
    cursor.close()
    context = dict()
    context['description'] = description
    context['rating'] = "%.1f" % rating
    context['taster'] = taster
    context['wine_title'] = wine_title
    print context
    return render_template("review.html", **context)

@app.route('/transaction',methods = ['GET'])
def transaction():
    print request.args
    print session

    test = []
    cursor3 = g.conn.execute("SELECT * FROM buys WHERE username = %s;",session['username'])
    print cursor3
    wine_title = []
    supplier_name = []
    quantity = []
    for result in cursor3:
        wine_title.append(result['wine_title'])
        supplier_name.append(result['supplier_name'])
        quantity.append(result['quantity'])
    cursor3.close()
    context = dict()
    context['wine_title'] = wine_title
    context['supplier_name'] = supplier_name
    context['quantity'] = quantity
    return render_template("transaction.html", **context)

@app.route('/winelist',methods = ['GET'])
def winelist():
    print request.args
    print session

    test = []
    cursor3 = g.conn.execute("SELECT * FROM winelist, app_user WHERE username = %s AND app_user.list_id = winelist.list_id;",session['username'])
    print cursor3
    wine_title = []

    for result in cursor3:
        wine_title.append(result['wine_title'])

    cursor3.close()
    context = dict()
    context['wine_title'] = wine_title

    return render_template("winelist.html", **context)

@app.route('/search')
def search():
  return render_template("search.html")


# Example of adding new data to the database
@app.route('/add', methods=['GET'])
def add():
  print request.args
  wine_title = request.args.get('wine_title')
  cmd = 'INSERT INTO winelist(list_id,wine_title) VALUES';

  cursor1 = g.conn.execute("SELECT list_id FROM app_user WHERE username = %s;",session['username'])
  for result in cursor1:
      list_id = result['list_id']
  g.conn.execute('INSERT INTO winelist(list_id,wine_title) VALUES (%s,%s)',(list_id,wine_title));
  return redirect('/wine?wine_title=' + wine_title.encode('utf8'))

@app.route('/remove', methods=['GET'])
def remove():
  print request.args
  wine_title = request.args.get('wine_title')

  cursor1 = g.conn.execute("SELECT list_id FROM app_user WHERE username = %s;",session['username'])
  for result in cursor1:
      list_id = result['list_id']
  g.conn.execute('DELETE FROM winelist WHERE list_id=%s AND wine_title=%s;',(list_id,wine_title));
  return redirect('/wine?wine_title=' + wine_title.encode('utf8'))


app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'


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
    Run the server using

        python server.py

    Show the help text using

        python server.py --help

    """

    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
