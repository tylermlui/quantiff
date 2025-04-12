import json
from os import environ as env
from urllib.parse import quote_plus, urlencode
import psycopg2
from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from flask import Flask, redirect, render_template, session, url_for
from flask import redirect, session, url_for

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

USER = env.get("user")
PASSWORD = env.get("password")
HOST = env.get("host")
PORT = env.get("pgport")
DBNAME = env.get("dbname")

app = Flask(__name__)
app.secret_key = env.get("APP_SECRET_KEY")
 
oauth = OAuth(app)

oauth.register( # Registers this app to Auth0 using OAuth
    "auth0",
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/openid-configuration'
)

def login_required(func): # function for protecting routes and ensuring that the user is logged in before accesing the route
    def secure_function():
        if "user" not in session:
            return redirect(url_for("login")) #returns user to login page if no session present
        return func()

    return secure_function

@app.route("/login")
def login():
    return oauth.auth0.authorize_redirect( #sends the user to auth0 to log in 
        redirect_uri=url_for("callback", _external=True) # sends user back to the /callback route 
    )

@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token() # will obtain the access_token and id_token
    session["user"] = token
    return redirect("/")

@app.route("/logout")
def logout():
    session.clear() #clears the users session including the tokens
    return redirect(
        "https://" + env.get("AUTH0_DOMAIN") #calls the auth0 endpoint to log out
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("home", _external=True),
                "client_id": env.get("AUTH0_CLIENT_ID"),
            },
            quote_via=quote_plus,
        )
    )

@app.route("/")
def home():
    return render_template("home.html", session=session.get('user'), pretty=json.dumps(session.get('user'), indent=4))

@app.route("/dashboard")
@login_required
def dashboard():
    try:
        print("Connecting with:", USER, HOST, DBNAME)
        connection = psycopg2.connect(
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT,
            dbname=DBNAME
        )
        print("Connection successful!")
        
        # Create a cursor to execute SQL queries
        cursor = connection.cursor()
        
        # Example query
        user_id = session["user"]["userinfo"]["sub"]
        cursor.execute(
            "INSERT INTO account_balance (user_id) VALUES (%s)",
            (user_id,)  # Safely insert user_id
        )
        cursor.execute("SELECT created_at, account_balance FROM users")
        results = cursor.fetchall()
        for row in results:
            print(row)
        # Close the cursor and connection
        cursor.close()
        connection.close()
        print("Connection closed.")

    except Exception as e:
        print(f"Failed to connect: {e}")

    return render_template("dashboard.html", user=session["user"], pretty=json.dumps(session.get('user'), indent=4))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=env.get("PORT", 3000))