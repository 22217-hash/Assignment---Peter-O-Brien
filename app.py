from flask import Flask, render_template, redirect, request, session
import sqlite3

app = Flask(__name__)
app.secret_key = "secretkey"


def connect_db():
    con = sqlite3.connect("identifier.sqlite")
    con.row_factory = sqlite3.Row
    return con


def is_admin():
    '''

    :return: This function returns either true or false dependig on if they are an admin or not
    '''
    if session["role"] == "admin":
        return True
    else:
        return False


@app.route('/')
def home():
    con = connect_db()
    cur = con.cursor()

    query = "SELECT * FROM events"
    cur.execute(query)
    event_list = cur.fetchall()

    con.close()
    return render_template("home.html", event_list=event_list)


@app.route("/signup", methods=['GET', 'POST'])
def render_signup_page():
    if request.method == 'POST':
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

        con = connect_db()
        cur = con.cursor()

        check_query = "SELECT * FROM users WHERE email = ?"
        cur.execute(check_query, (email,))
        existing_user = cur.fetchone()

        if existing_user is not None:
            con.close()
            return redirect("/signup?error=email+already+exists")

        insert_query = "INSERT INTO users (fname, lname, email, password, role) VALUES (?,?,?,?,?)"
        cur.execute(insert_query, (fname, lname, email, password, role))
        con.commit()
        con.close()

        return redirect("login")

    return render_template("signup.html")


@app.route('/login', methods=['GET', 'POST'])
def render_login_page():
    error = request.form.get("error")

    if request.method == 'POST':
        email = request.form.get('user_email').lower().strip()
        password = request.form.get('user_password').strip()

        con = connect_db()
        cur = con.cursor()

        query = "SELECT * FROM users WHERE email = ? AND password = ?"
        cur.execute(query, (email, password))
        user = cur.fetchone()

        con.close()

        if user is None:
            return redirect("/login?error=invalid+email+or+password")

        session["user_id"] = user["user_id"]
        session["fname"] = user["fname"]
        session["role"] = user["role"]

        return redirect("/")

    return render_template("login.html")


@app.route('/logout')
def logout():
    session.clear()
    return redirect("/")


@app.route('/add_event', methods=['GET', 'POST'])
def add_event():
    if "user_id" not in session:
        return redirect("/login?error=log+in+first")

    error = request.args.get("error")

    if request.method == 'POST':
        event_name = request.form.get('event_name').strip()
        event_date = request.form.get('event_date').strip()
        event_location = request.form.get('event_location').strip()
        event_description = request.form.get('event_description').strip()

        if event_name == "" or event_date == "" or event_location == "" or event_description == "":
            return redirect("/add_event?error=fill+in+all+boxes")

        con = connect_db()
        cur = con.cursor()

        query = """
        INSERT INTO events (event_name, event_date, event_location, event_description, fk_user_id)
        VALUES (?,?,?,?,?)
        """
        cur.execute(query, (event_name, event_date, event_location, event_description, session["user_id"]))
        con.commit()
        con.close()

        return redirect("/")
    return render_template("add_event.html")


@app.route('/book_event/<event_id>', methods=['GET', 'POST'])
def book_event(event_id):
    if "user_id" not in session:
        return redirect("/login?error=log+in+first")

    con = connect_db()
    cur = con.cursor()

    query = "SELECT * FROM events WHERE event_id = ?"
    cur.execute(query, (event_id,))
    chosen_event = cur.fetchone()

    if request.method == 'POST':
        tickets = request.form.get("tickets").strip()

        if tickets == "":
            con.close()
            return redirect("/bookevent/{event_id}")

        insert_query = "INSERT INTO bookings (fk_user_id, fk_event_id, tickets) VALUES (?,?,?)"
        cur.execute(insert_query, (session["user_id"], event_id, tickets))
        con.commit()
        con.close()

        return redirect("/my_bookings")

    con.close()
    return render_template("book_event.html", chosen_event=chosen_event)


@app.route('/my_bookings')
def my_bookings():
    if "user_id" not in session:
        return redirect("/login?error=log+in+first")

    con = connect_db()
    cur = con.cursor()

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


if __name__ == '__main__':
    app.run(debug=True, port=5001)
