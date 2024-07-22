from flask import Blueprint, render_template, session, url_for, redirect, current_app, flash, request
from authlib.integrations.flask_client import OAuth, OAuthError
from datetime import datetime
from flask_login import LoginManager
from flask_login import login_user, UserMixin, login_required
from dotenv import load_dotenv
import os
import requests
import logging
import pytz
import psycopg2

## load envs
# get the directory of the current file (`auth.py`)
current_dir = os.path.dirname(os.path.abspath(__file__))
# from this directory get the root directory
root_dir = os.path.dirname(os.path.dirname(current_dir))
# construct the full path to the .env file
env_path = os.path.join(root_dir, "important.env")
# load the .env file
load_dotenv(env_path)
# load env vars
google_client_id = os.getenv("GOOGLE_CLIENT_ID")
google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
google_redirect_url = os.getenv("GOOGLE_REDIRECT_URL")
microsoft_client_id = os.getenv("MICROSOFT_CLIENT_ID")
microsoft_client_secret=os.getenv("MICROSOFT_CLIENT_SECRET")
microsoft_redirect_url = os.getenv("MICROSOFT_REDIRECT_URL")
twitter_client_id = os.getenv("TWITTER_CLIENT_ID")
twitter_client_secret=os.getenv("TWITTER_CLIENT_SECRET")
twitter_redirect_url = os.getenv("TWITTER_REDIRECT_URL")

# create blueprint
auth = Blueprint("auth", __name__, static_folder="static", template_folder="templates")

# fatcory function to create OAuth object
def create_oauth(app):
    oauth = OAuth(app) #OAuth is a global configuration that applies to your entire Flask application, not just to a specific blueprint like 'auth.py'. So its init and config are usually done inside app.py

    ## config OAuth providers
    # google (oauth 2.0)
    oauth.register(
        name="google",
        client_id=google_client_id,
        client_secret=google_client_secret,
        access_token_url="https://oauth2.googleapis.com/token",
        authorize_url="https://accounts.google.com/o/oauth2/auth",
        client_kwargs={"scope": "openid profile"},
        redirect_uri=google_redirect_url,
        jwks_uri="https://www.googleapis.com/oauth2/v3/certs"
    )

    # microsoft (oauth 2.0)
    oauth.register(
        name="microsoft",
        client_id=microsoft_client_id,
        client_secret=microsoft_client_secret,
        access_token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
        authorize_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        client_kwargs={"scope": "openid profile User.Read"}, # User.Read allows 'sign in & read user profile'
        redirect_uri=microsoft_redirect_url,
        jwks_uri="https://login.microsoftonline.com/common/discovery/v2.0/keys"
    )

    # twitter (oauth 1.0)
    oauth.register(
        name="twitter",
        client_id=twitter_client_id,
        client_secret=twitter_client_secret,
        request_token_url="https://api.twitter.com/oauth/request_token",
        access_token_url="https://api.twitter.com/oauth/access_token",
        authorize_url="https://api.twitter.com/oauth/authenticate",
        api_base_url="https://api.twitter.com/1.1/",
        redirect_uri=twitter_redirect_url
    )

    return oauth

## route
@auth.route("/home")
def home():
    return render_template("home.html")

@auth.route("/login")
def login():
    return render_template("login.html")

@auth.route("/privacyPolicy")
def privacy_policy():
    return render_template("privacy_policy.html")

@auth.route("/termsOfService")
def terms_of_service():
    return render_template("terms_of_service.html")

@auth.route("/setTimezone", methods=["GET", "POST"])
@login_required
def set_timezone():
    if request.method == "POST":
        user_timezone = request.form.get("timezone")
        ######### CHECK #########
        logging.info(f"USER TIMEZONE FROM FORM: {user_timezone}\n\n")
        if not user_timezone:
            user_timezone = "UTC"
        session["user_timezone"] = user_timezone
        return redirect(url_for("pomodoro.timer"))
    
    return render_template("set_timezone.html")

# route for OAuth login
@auth.route("/login/google", methods=["GET", "POST"])
def login_google():
    oauth = current_app.config["oauth"]
    redirect_uri = url_for("auth.authorize_google", _external=True, _scheme="https") # 'external=True' ensures full URL is generated
    return oauth.google.authorize_redirect(redirect_uri)

@auth.route("/login/microsoft", methods=["GET", "POST"])
def login_microsoft():
    oauth = current_app.config["oauth"]
    redirect_uri = url_for("auth.authorize_microsoft", _external=True, _scheme="https")
    return oauth.microsoft.authorize_redirect(redirect_uri)

@auth.route("/login/twitter", methods=["GET", "POST"])
def login_twitter():
    oauth = current_app.config["oauth"]
    redirect_uri = url_for("auth.authorize_twitter", _external=True, _scheme="https")
    return oauth.twitter.authorize_redirect(redirect_uri)

# route for OAuth callback
@auth.route("/login/google/callback")
def authorize_google():
    try:
        oauth = current_app.config["oauth"]
        token = oauth.google.authorize_access_token()
        if not token:
            # flash("Some message", "category")
            flash("Authentication failed: No access token received.", "error") # The 'flash' function in Flask is used to send temporary messages from the backend to the frontend.
            return redirect(url_for("auth.login"))
        resp = oauth.google.get("https://www.googleapis.com/oauth2/v3/userinfo")
        resp.raise_for_status()
        profile = resp.json()
        session["logged_in"] = True # 'session' can be modified or accessed from any route or part of your application that has access to Flask's context.
        session["last_login_time"] = datetime.now(pytz.utc)
        openid = profile["sub"]
        name = profile["given_name"]
        oauth_provider = "Google"

        user = load_or_create_user(openid, name, oauth_provider)
        login_user(user)
        return redirect(url_for("auth.set_timezone"))
        
    except OAuthError as oe:
        # Logging in Flask (and more generally in Python) is used for recording information about the application’s operation. 
        # This can include errors, informational messages, warnings, and debugging output. It’s essential for monitoring the application's health, debugging issues, and keeping track of what your application is doing, especially in production.
        logging.error(f"OAuthError during Google authentication: {oe.description}")
        flash("Authentication error occurred.", "error")
    except requests.exceptions.HTTPError as he:
        logging.error(f"HTTPError during API call to Google: Status code {he.response.status_code}, Response text: {he.response.text}")
        flash("Failed to fetch user information from Google.", "error")
    except Exception as e:
        logging.error(f"Unexpected error in Google OAuth process: {e}")
        flash("An unexpected error occurred, please try again.", "error")
    return redirect(url_for("auth.login"))

@auth.route("/login/microsoft/callback")
def authorize_microsoft():
    try:
        oauth = current_app.config["oauth"]
        token = oauth.microsoft.authorize_access_token()
        if not token:
            flash("Authentication failed: No access token received.", "error")
            return redirect(url_for("auth.login"))
        resp = oauth.microsoft.get("https://graph.microsoft.com/v1.0/me")
        resp.raise_for_status()
        profile = resp.json()
        session["logged_in"] = True
        session["last_login_time"] = datetime.now(pytz.utc)
        openid = profile["id"]
        name = profile["givenName"]
        oauth_provider = "Microsoft"

        user = load_or_create_user(openid, name, oauth_provider)
        login_user(user)
        return redirect(url_for("auth.set_timezone"))
        
    except OAuthError as oe:
        logging.error(f"OAuthError during Microsoft authentication: {oe.description}")
        flash("Authentication error occurred.", "error")
    except requests.exceptions.HTTPError as he:
        logging.error(f"HTTPError during API call to Microsoft: Status code {he.response.status_code}, Response text: {he.response.text}")
        flash("Failed to fetch user information from Microsoft.", "error")
    except Exception as e:
        logging.error(f"Unexpected error in Microsoft OAuth process: {e}")
        flash("An unexpected error occurred, please try again.", "error")
    return redirect(url_for("auth.login"))

@auth.route("/login/twitter/callback")
def authorize_twitter():
    try:
        oauth = current_app.config["oauth"]
        token = oauth.twitter.authorize_access_token()
        if not token:
            flash("Authentication failed: No access token received.", "error")
            return redirect(url_for("auth.login"))
        resp = oauth.twitter.get("account/verify_credentials.json")
        resp.raise_for_status()
        profile = resp.json()
        session["logged_in"] = True
        session["last_login_time"] = datetime.now(pytz.utc)
        openid = profile["id_str"]
        name = profile["name"]
        oauth_provider = "Twitter"

        user = load_or_create_user(openid, name, oauth_provider)
        login_user(user)
        return redirect(url_for("auth.set_timezone"))
        
    except OAuthError as oe:
        logging.error(f"OAuthError during Twitter authentication: {oe.description}")
        flash("Authentication error occurred.", "error")
    except requests.exceptions.HTTPError as he:
        logging.error(f"HTTPError during API call to Twitter: Status code {he.response.status_code}, Response text: {he.response.text}")
        flash("Failed to fetch user information from Twitter.", "error")
    except Exception as e:
        logging.error(f"Unexpected error in Twitter OAuth process: {e}")
        flash("An unexpected error occurred, please try again.", "error")
    return redirect(url_for("auth.login"))

# db class & functions
class User(UserMixin): # 'UserMixin' provides default implementations for properties and methods that Flask-Login expects (like is_authenticated, is_active, is_anonymous, and get_id)
    def __init__(self, userIdPar):
        self.id = userIdPar # UserMixin expects an 'id' attribute that uniquely identifies the user

#### When a user logs into your application and login_user(user) is called, 
#### Flask-Login stores the user class in the session. 
#### On subsequent requests, Flask-Login retrieves the user ID from the session and calls the load_user function to get the actual user object. 
#### This user object is then made available through current_user during the request.

login_manager = LoginManager()

@login_manager.user_loader # Flask-Login expects the 'load_user' function to return an instance of a user object
def load_user(user_id):
    return User(user_id) # returns the user object

def load_or_create_user(openidPar, usernamePar, oauthProviderPar):
    '''
    Retrieve or create a user if the user is not found in the database.
    Returns the user object.
    '''
    try:
        # Connect to PostgreSQL database
        conn = psycopg2.connect(os.environ["DATABASE_URL"], sslmode="require")
        cur = conn.cursor()
        cur.execute("SELECT * FROM \"user\" WHERE openid = %s", (openidPar,))
        # In Postgres
        # 'fetchall()' returns an array of tuples
        # 'fetchone()' returns a single tuple that has multiple items / None
        user = cur.fetchone()

        if user is None:
            if usernamePar == "" or usernamePar == None:
                usernamePar = "Pomo"
            cur.execute("INSERT INTO \"user\" (openid, username, oauth_provider) VALUES (%s, %s, %s) RETURNING id",
                        (openidPar, usernamePar, oauthProviderPar))
            user_id = cur.fetchone()[0] # 'id' of the newly created user is returned
            conn.commit()
            logging.info("User created successfully.")
            return User(user_id)
        else:
            logging.info("User found.")
            return User(user[0])  # Assuming the first column is the user id

    except psycopg2.Error as e:
        logging.error(f"Database error: {e}")
        conn.rollback()  # Rollback the transaction on error
        raise e
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        raise e
    finally:
        cur.close()
        conn.close()
