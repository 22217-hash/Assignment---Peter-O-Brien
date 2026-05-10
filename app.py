from flask import Flask, render_template, redirect, request, session
import sqlite3
from flask_bcrypt import Bcrypt

app = Flask(__name__)
bcrypt = Bcrypt(app)
app.secret_key = "secretkey"



# connects to the SQLite database and allows rowsto be accessed like dictionaries
def connect_db():
    con = sqlite3.connect("identifier.sqlite")
    con.row_factory = sqlite3.Row
    return con


def is_admin():
    # checks if user is an admin bassed on their session role
    if session["role"] == "admin":
        return True
    else:
        return False

# displays all events on the home page
@app.route('/')
def home():
    con = connect_db()
    cur = con.cursor()
    # Get all events from the database
    query = "SELECT * FROM events"
    cur.execute(query)
    event_list = cur.fetchall()

    con.close()
    return render_template("home.html", event_list=event_list)

# handles user signup and stores new users in the database
@app.route("/signup", methods=['GET', 'POST'])
def render_signup_page():
    if request.method == 'POST':
        # Get user input from form
        fname = request.form.get('user_fname').title().strip()
        lname = request.form.get('user_lname').title().strip()
        email = request.form.get('user_email').lower().strip()
        password = request.form.get('user_password').strip()
        password2 = request.form.get('user_password2').strip()
        role = request.form.get('user_role').strip().lower()

        if fname == "" or lname == "" or email == "" or password == "" or password2 == "":
            return redirect("/signup?error=fill+in+all+boxes")

        if password != password2:
            return redirect("/signup?error=passwords+do+not+match")

        if len(password) < 8:
            return redirect("/signup?error=password+must+be+at+least+8+characters")

        hashed_password = bcrypt.generate_password_hash(password)

        con = connect_db()
        cur = con.cursor()
        # check if email already exists
        check_query = "SELECT * FROM users WHERE email = ?"
        cur.execute(check_query, (email,))
        existing_user = cur.fetchone()

        if existing_user is not None:
            con.close()
            return redirect("/signup?error=email+already+exists")
        # Insert new user into database
        insert_query = "INSERT INTO users (fname, lname, email, password, role) VALUES (?,?,?,?,?)"
        cur.execute(insert_query, (fname, lname, email, hashed_password, role))
        con.commit()
        con.close()

        return redirect("/login")
    error = request.args.get("error")
    return render_template("signup.html", error=error)

# Handles user login and checks details
@app.route('/login', methods=['GET', 'POST'])
def render_login_page():
    # Get user details from form
    if request.method == 'POST':
        email = request.form.get('user_email').lower().strip()
        password = request.form.get('user_password').strip()

        con = connect_db()
        cur = con.cursor()
        # Get user by email from database
        query = "SELECT * FROM users WHERE email = ?"
        cur.execute(query, (email, ))
        user = cur.fetchone()

        con.close()
        # Check entered password against hashed password
        if user is None:
            return redirect("/login?error=invalid+email+or+password")

        if not bcrypt.check_password_hash(user["password"], password):
            return redirect("/login?error=invalid+email+or+password")
        # Store user details in session so they stay logged in
        session["user_id"] = user["user_id"]
        session["fname"] = user["fname"]
        session["role"] = user["role"]

        return redirect("/")
    error = request.args.get("error")
    return render_template("login.html", error=error)

# Logs the user out by clearing session data
@app.route('/logout')
def logout():
    session.clear()
    return redirect("/")

# Allows admin users to add new events
@app.route('/add_event', methods=['GET', 'POST'])
# Make sure user is logged in
def add_event():
    if "user_id" not in session:
        return redirect("/login?error=log+in+first")

    error = request.args.get("error")
    # Get event details from form
    if request.method == 'POST':
        event_name = request.form.get('event_name').strip()
        event_date = request.form.get('event_date').strip()
        event_location = request.form.get('event_location').strip()
        event_description = request.form.get('event_description').strip()
        # Check all fields are filled
        if event_name == "" or event_date == "" or event_location == "" or event_description == "":
            return redirect("/add_event?error=fill+in+all+boxes")

        con = connect_db()
        cur = con.cursor()
        # Insert new event into database
        query = """
        INSERT INTO events (event_name, event_date, event_location, event_description, fk_user_id)
        VALUES (?,?,?,?,?)
        """
        cur.execute(query, (event_name, event_date, event_location, event_description, session["user_id"]))
        con.commit()
        con.close()

        return redirect("/")

    return render_template("add_event.html", error=error)

# Allows users to book tickets for an event
@app.route('/book_event/<event_id>', methods=['GET', 'POST'])
def book_event(event_id):
    if "user_id" not in session:
        return redirect("/login?error=log+in+first")

    con = connect_db()
    cur = con.cursor()
    # Get selected event from database
    query = "SELECT * FROM events WHERE event_id = ?"
    cur.execute(query, (event_id,))
    chosen_event = cur.fetchone()
    # Get number of tickets entered
    if request.method == 'POST':
        tickets = request.form.get("tickets").strip()

        if tickets == "":
            con.close()
            return redirect(f"/book_event/{event_id}?error=fill+in+tickets")
        # Save booking to database
        insert_query = "INSERT INTO bookings (fk_user_id, fk_event_id, tickets) VALUES (?,?,?)"
        cur.execute(insert_query, (session["user_id"], event_id, tickets))
        con.commit()
        con.close()

        return redirect("/my_bookings")

    con.close()
    error = request.args.get("error")
    return render_template("book_event.html", chosen_event=chosen_event, error=error)

# Shows all bookings for the logged in user
@app.route('/my_bookings')
def my_bookings():
    if "user_id" not in session:
        return redirect("/login?error=log+in+first")

    con = connect_db()
    cur = con.cursor()
    # Join bookings with events to display event details
    query = """
    SELECT bookings.*, events.event_name, events.event_date
    FROM bookings
    JOIN  events ON bookings.fk_event_id = events.event_id
    WHERE bookings.fk_user_id = ?
    """

    cur.execute(query, (session["user_id"],))
    booking_list = cur.fetchall()

    con.close()
    return render_template("my_bookings.html", booking_list=booking_list)

# Allows user to cancel a booking
@app.route('/delete_booking/<booking_id>')
def delete_booking(booking_id):
    if "user_id" not in session:
        return redirect("/login")

    con = connect_db()
    cur = con.cursor()
    # Delete booking only if it belongs to the current user
    query = "DELETE FROM bookings WHERE booking_id = ? AND fk_user_id = ?"
    cur.execute(query, (booking_id, session["user_id"]))

    con.commit()
    con.close()

    return redirect("/my_bookings")

if __name__ == '__main__':
    app.run(debug=True, port=5005)
