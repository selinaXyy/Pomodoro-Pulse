from flask import Flask, render_template, session, url_for, redirect, flash, request
from flask_wtf.csrf import CSRFProtect
from datetime import datetime, timedelta
from flask_bootstrap import Bootstrap5
from auth.auth import create_oauth, auth, login_manager
from pomodoro.pomodoro import pomodoro
from dotenv import load_dotenv
import os
import logging
import pytz

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
flask_secret_key = os.getenv("FLASK_SECRET_KEY")

# Configure logging
logging.basicConfig(
    level=logging.INFO, # --> INFO level and above (WARNING, ERROR, CRITICAL) messages will be logged
    format="%(asctime)s - %(levelname)s - %(message)s", # --> defines the format string for the log messages
    datefmt="%Y-%m-%d %H:%M:%S", # --> specifies the format of the date/time string.
    )

# create app
app = Flask(__name__)
app.secret_key = flask_secret_key
csrf = CSRFProtect(app)

# init app with extensions (Boostrap5, LoginManager)
bootstrap = Bootstrap5(app)
login_manager.init_app(app)
login_manager.login_view = "auth.login"

# Register blueprints
app.register_blueprint(auth, url_prefix="/auth")
app.register_blueprint(pomodoro, url_prefix="/pomodoro")
# Create OAuth instance using factory function
oauth = create_oauth(app)
# Ensure the oauth instance is global
app.config["oauth"] = oauth

@app.context_processor # A context processor runs before templates are rendered and injects its return values into all the template context.
def inject_year():
    return {"current_year": datetime.now().year}

@app.route("/")
def index():
    # check for revisits
    if session.get("logged_in"): # None is considered a falsy value
        last_login_time = session.get("last_login_time")
        now = datetime.now(pytz.utc)  # Make datetime.now timezone-aware using UTC
        if last_login_time and (now - last_login_time < timedelta(days=3)): # compare datetime object to datetime object
            return redirect(url_for("auth.set_timezone"))
        else:
            flash("Your session has expired. Please log in again to continue.", "error")
            return redirect(url_for("auth.home"))
    else:
        return redirect(url_for("auth.home"))

if __name__ == "__main__":
    # The PORT environment variable on platforms like Heroku is set by the hosting infrastructure itself. 
    # When you deploy an application to Heroku, the platform automatically assigns a port and sets the PORT environment variable to that port number for your application to use.
    port = int(os.environ.get("PORT", 5000))  # Default to 5000 if PORT not set
    app.run(host="0.0.0.0", port=port)