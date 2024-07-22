from flask import Blueprint, render_template, session, url_for, redirect, current_app, flash, current_app, request, jsonify
from flask_wtf import FlaskForm
from flask_login import logout_user, current_user, login_required
from wtforms import StringField, SubmitField, SelectField, TextAreaField, validators, Form
from wtforms.validators import DataRequired
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from flask_babel import _
from dotenv import load_dotenv
import os
import logging
import smtplib
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
smtp_email = os.getenv("SMTP_EMAIL")
smtp_password = os.getenv("SMTP_PASSWORD")

pomodoro = Blueprint("pomodoro", __name__, static_folder="static", template_folder="templates")

def format_time(totalMinutesPar):
    """
    Converts a total number of minutes into a human-readable format with hours and minutes.

    Args:
    total_minutes (int): The total number of minutes to convert.

    Returns:
    str: A formatted string representing the time in hours and minutes.
    """
    if totalMinutesPar < 60:
        return f"{totalMinutesPar}m"
    else:
        hrs = int(totalMinutesPar / 60)
        mins = totalMinutesPar % 60
        if hrs == 1:
            if mins == 0:
                return "1h"
            else:
                return f"1h{mins}m"
        else:
            if mins == 0:
                return f"{hrs}h"
            else:
                return f"{hrs}h{mins}m"

class HelpForm(FlaskForm):
    email = StringField(
        label="Your Email Address", 
        validators=[
            validators.Length(min=6, message=_("Please make sure you entered a valid email address.")), 
            validators.Email(message=_("Invalid email address."))
        ],
        render_kw={
            "placeholder": "example@email.com"
    })

    subject_choices = [
        ("issue", "Reporting an Issue"), # internal value, user-facing label
        ("feedback", "Providing Feedback"),
        ("suggestion", "Offering a Suggestion")
    ]
    subject = SelectField(
        "Select the Subject Type", 
        choices=subject_choices,
        default="feedback"
    )

    message = TextAreaField(  # Use TextAreaField for multi-line messages
        label="Your Questions/Feedback",
        validators=[DataRequired()],
        render_kw={
            "placeholder": "Enter your questions or feedback here.",
        } 
    )

    submit = SubmitField("Submit")

@pomodoro.route("/timer", methods=["GET"])
@login_required
def timer():
    conn = psycopg2.connect(os.environ["DATABASE_URL"], sslmode="require")
    cur = conn.cursor()
    cur.execute("SELECT username FROM \"user\" WHERE id = %s", (current_user.id,))
    username = cur.fetchone()[0]
    cur.close()
    conn.close()
    ######### CHECK #########
    logging.info(f"\n\nUSER ID: {current_user.id}\nUSER TIMEZONE: {session.get("user_timezone")}\n\n")
    return render_template("timer.html", username=username)

@pomodoro.route("/addSession", methods=["POST"]) # Flask-WTF handles the CSRF validation automatically for you whenever a form submission or a POST request occurs
@login_required
def add_session():
    # store time in UTC by default
    utc_now_str = datetime.now(pytz.utc).isoformat()
    session_minutes = 100
    try:
        # Connect to PostgreSQL database using the DATABASE_URL from your environment
        conn = psycopg2.connect(os.environ["DATABASE_URL"], sslmode="require")
        cur = conn.cursor()
        cur.execute("INSERT INTO session (user_id, minutes, session_date) VALUES (%s, %s, %s)",
                    (current_user.id, session_minutes, utc_now_str))
        conn.commit()  # Commit the transaction to save changes
        return jsonify({"status": "success", "message": "Session added successfully"}), 201

    except psycopg2.Error as e:
        if conn:
            conn.rollback()  # Rollback transaction on error
        logging.error(f"Database error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        # Ensure that the cursor and connection are closed properly
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


@pomodoro.route("/tips", methods=["GET", "POST"])
@login_required
def tips():
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"], sslmode="require")
        cur = conn.cursor()

        if request.method == "POST":
            tip_title = request.form["title"]
            tip_content = request.form["content"]
            # Insert data into the tip table
            cur.execute("INSERT INTO tip (user_id, tip_title, tip_content) VALUES (%s, %s, %s)",
                        (current_user.id, tip_title, tip_content))
            conn.commit()
            return redirect(url_for("pomodoro.tips"))

        cur.execute("SELECT username FROM \"user\" WHERE id = %s", (current_user.id,))
        username = cur.fetchone()[0]

        # Load user tips (titles & contents) --> GET
        user_tips = []
        # Check if user has added any tips before
        cur.execute("SELECT user_id FROM tip WHERE user_id = %s", (current_user.id,))
        tip_exists = cur.fetchone()

        if tip_exists:
            cur.execute("SELECT id, tip_title, tip_content FROM tip WHERE user_id = %s ORDER BY id DESC", (current_user.id,))
            tips_data = cur.fetchall()
            # Convert fetched data into a list of dictionaries
            user_tips = [{"tip_id": tip[0], "tip_title": tip[1], "tip_content": tip[2]} for tip in tips_data]

        return render_template("tips.html", user_tips=user_tips, username=username)

    except psycopg2.Error as e:
        flash(f"A database error occurred: {e}", "error")
        logging.error(f"Database error: {e}")
        # Rollback transaction on error
        if conn:
            conn.rollback()
        return redirect(url_for("pomodoro.tips"))

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@pomodoro.route("/addTip")
@login_required
def addTip():
    return render_template("addTip.html")

@pomodoro.route("/deleteTip", methods=["POST"])
@login_required
def deleteTip():
    try:
        data = request.get_json()
        if not data:
            logging.error("No data received in request")
            return jsonify({"status": "error", "message": "No data received"}), 400

        tip_id = data.get("tipId")
        if not tip_id:
            logging.error("No tip ID provided")
            return jsonify({"status": "error", "message": "No tip ID provided"}), 400

        # deletion logic
        conn = psycopg2.connect(os.environ["DATABASE_URL"], sslmode="require")
        cur = conn.cursor()
        cur.execute("DELETE FROM tip WHERE id = %s", (tip_id,))
        conn.commit()

        logging.info(f"Tip ID {tip_id} deleted successfully")
        return jsonify({"status": "success", "message": "Tip deleted successfully"}), 200

    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        if conn:
            conn.close()
        if cur:
            cur.close()

@pomodoro.route("/profile")
@login_required
def profile():
    # name(user), minutes(session)/total, minutes(session)/daily
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"], sslmode="require")
        cur = conn.cursor()
        cur.execute("SELECT username FROM \"user\" WHERE id = %s", (current_user.id,))
        username = cur.fetchone()[0]
        logging.info(f"\n\nUSERNAME: {username}\n\n")

        # Check if user has completed any sessions before
        cur.execute("SELECT user_id FROM session WHERE user_id = %s", (current_user.id,))
        session_exists = cur.fetchone()
        total_time = "0m"
        today_time = "0m"
        
        if session_exists:
            cur.execute("SELECT SUM(minutes) FROM session WHERE user_id = %s", (current_user.id,))
            total_time = cur.fetchone()[0]

            ## Handle timezone conversion and date checking
            # get user timezone in str format
            user_timezone_str = session.get("user_timezone", "UTC")
            # turn user timezone str into a user timezone obj
            user_timezone = ZoneInfo(user_timezone_str)
            # get time now obj in utc, make it time aware
            utc_now = datetime.now(ZoneInfo("UTC"))
            # turn utc time now obj into a user time now obj
            user_local_time = utc_now.astimezone(user_timezone)
            # turn the obj back to a str
            user_current_date_str = user_local_time.strftime("%Y-%m-%d")

            cur.execute("SELECT minutes, session_date FROM session WHERE user_id = %s", (current_user.id,))
            time_and_date = cur.fetchall()
            
            if time_and_date:
                today_time = 0
                for minutes, session_date in time_and_date:
                    # turn the full utc time str into a utc time obj
                    session_date_utc = datetime.fromisoformat(session_date)
                    # turn utc time obj into user local time str
                    session_date_local_str = session_date_utc.astimezone(user_timezone).strftime("%Y-%m-%d")
                    if session_date_local_str == user_current_date_str:
                        today_time += minutes

            total_time = format_time(total_time)
            today_time = format_time(today_time)

        return render_template("profile.html", username=username, total_time=total_time, today_time=today_time)

    except psycopg2.Error as e:
        flash(f"A database error occurred: {e}", "error")
        logging.error(f"Database error: {e}")
        return render_template("profile.html", username="Error", total_time="0m", today_time="0m")
    except Exception as e:
        flash("An unexpected error occurred. Please try again.", "error")
        logging.error(f"An unexpected error occurred: {e}")
        return render_template("profile.html", username="Error", total_time="0m", today_time="0m")
    finally:
        if conn:
            conn.close()
        if cur:
            cur.close()

@pomodoro.route("/help", methods=["GET", "POST"])
@login_required
def help():
    conn = psycopg2.connect(os.environ["DATABASE_URL"], sslmode="require")
    cur = conn.cursor()
    cur.execute("SELECT username FROM \"user\" WHERE id = %s", (current_user.id,))
    username = cur.fetchone()[0]
    conn.close()
    cur.close()

    form = HelpForm(csrf_token=current_app.secret_key)
    if form.validate_on_submit():
        user_submission = form.data.values()
        data_num = 3
        data_cnt = 0
        data = []

        for submission in user_submission:
            if data_cnt >= data_num:
                break
            data.append(submission)
            data_cnt += 1

        # send email to developer
        message = "Subject:" + data[1].title() + " from Pomodoro Pulse\n\nUser email: " + data[0] + "\nUser Message: " + data[2]

        smtp_port = int(os.getenv('SMTP_PORT', 587)) # SMTP_PORT env variable was set in the Heroku environment
        with smtplib.SMTP("smtp.gmail.com", port=smtp_port) as connection:
            connection.starttls()
            connection.login(user=smtp_email, password=smtp_password)
            connection.sendmail(
                from_addr=smtp_email,
                to_addrs="yiyangxue.xyy@gmail.com",
                msg=message
            )
        # change this to help-success later
        return render_template("help-success.html")

    else:
        return render_template("help.html", form=form, username=username)

@pomodoro.route("/logout")
@login_required
def logout():
    logout_user()
    session["logged_in"] = False
    session["last_login_time"] = datetime.now(pytz.utc)
    return redirect(url_for("auth.login"))