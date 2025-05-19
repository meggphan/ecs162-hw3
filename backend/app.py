from flask import Flask, request, jsonify, send_from_directory, session, redirect
from flask_cors import CORS
from pymongo import MongoClient
from authlib.integrations.flask_client import OAuth
from authlib.common.security import generate_token
import os
import requests
from datetime import datetime
from bson import ObjectId

# Flask setup
app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)
app.secret_key = os.urandom(24)

# MongoDB setup
mongo = MongoClient(os.getenv("MONGO_URI", "mongodb://mongo:27017/"))
db = mongo["nyt"]
comments = db["comments"]

# OIDC (Dex) setup
oauth = OAuth(app)
nonce = generate_token()
oauth.register(
    name=os.getenv("OIDC_CLIENT_NAME"),
    client_id=os.getenv("OIDC_CLIENT_ID"),
    client_secret=os.getenv("OIDC_CLIENT_SECRET"),
    authorization_endpoint="http://dex:5556/auth",
    token_endpoint="http://dex:5556/token",
    jwks_uri="http://dex:5556/keys",
    userinfo_endpoint="http://dex:5556/userinfo",
    client_kwargs={'scope': 'openid email profile'}
)

@app.route('/login')
def login():
    redirect_uri = os.getenv("DEX_REDIRECT_URI", "http://localhost:8000/auth")
    return oauth.oidc.authorize_redirect(redirect_uri)

@app.route('/auth')
def auth():
    token = oauth.oidc.authorize_access_token()
    user = oauth.oidc.parse_id_token(token, nonce=nonce)
    session["user"] = user
    return redirect("/")

@app.route('/logout')
def logout():
    session.clear()
    return redirect("/")

@app.route('/api/user')
def get_user():
    return jsonify(session.get("user"))

@app.route('/api/key')
def get_api_key():
    return jsonify({'apiKey': os.getenv('NYT_API_KEY')})

@app.route('/api/articles')
def get_articles():
    query = "Davis OR Sacramento"
    url = "https://api.nytimes.com/svc/search/v2/articlesearch.json"
    params = {
        "q": query,
        "api-key": os.getenv("NYT_API_KEY")
    }
    res = requests.get(url, params=params)
    return jsonify(res.json())

@app.route('/api/comments', methods=["GET", "POST", "DELETE"])
def comment_handler():
    if request.method == "GET":
        article_id = request.args.get("article_id")
        all_comments = list(comments.find({"article_id": article_id}))
        for c in all_comments:
            c["_id"] = str(c["_id"])
        return jsonify(all_comments)

    user = session.get("user")
    if not user:
        return jsonify({"error": "Not authenticated"}), 401

    if request.method == "POST":
        data = request.json
        new_comment = {
            "article_id": data["article_id"],
            "user_email": user["email"],
            "text": data["text"],
            "timestamp": datetime.utcnow(),
            "redacted": False,
            "removed": False
        }
        comments.insert_one(new_comment)
        return jsonify({"status": "Comment added"})

    if request.method == "DELETE":
        comment_id = request.args.get("id")
        moderator = user.get("email", "").endswith("@ucdavis.edu")
        if moderator:
            comments.update_one({"_id": ObjectId(comment_id)}, {"$set": {"removed": True}})
            return jsonify({"status": "Comment removed"})
        return jsonify({"error": "Unauthorized"}), 403

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    static_path = os.getenv("STATIC_PATH", "dist")
    if path != "" and os.path.exists(os.path.join(static_path, path)):
        return send_from_directory(static_path, path)
    return send_from_directory(static_path, "index.html")

if __name__ == "__main__":
    debug = os.getenv("FLASK_ENV") != "production"
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)), debug=debug)
