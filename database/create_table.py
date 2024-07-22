# CREATE TABLE "user" (
#     id SERIAL PRIMARY KEY, 
#     openid TEXT NOT NULL UNIQUE, 
#     username TEXT NOT NULL, 
#     oauth_provider TEXT NOT NULL
# );

# CREATE TABLE session (
#     id SERIAL PRIMARY KEY, 
#     user_id INTEGER NOT NULL REFERENCES "user"(id), 
#     minutes INTEGER NOT NULL, 
#     session_date TEXT NOT NULL
# );


# CREATE TABLE tip (
#     id SERIAL PRIMARY KEY, 
#     user_id INTEGER NOT NULL REFERENCES "user"(id), 
#     tip_title TEXT, 
#     tip_content TEXT
# );