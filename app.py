from flask import Flask, render_template
import os

# Initialize Flask app
app = Flask(__name__)

# Home route
@app.route("/")
def index():
    q = "Hello, Hackathon! 🚀"  # You can replace this with any dynamic logic
    return render_template("index.html", q=q)

# Health check route (optional for uptime checks)
@app.route("/health")
def health():
    return {"status": "running"}, 200
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/upload")
def upload():
    return render_template("upload.html")

@app.route("/ping")
def ping():
    return render_template("ping.html")

@app.route("/fetch")
def fetch():
    return render_template("fetch.html")

@app.route("/admin")
def admin():
    return render_template("admin.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/register")
def register():
    return render_template("register.html")

# Main entry point
if __name__ == "__main__":
    # Get port number from environment variable (Render, Railway, etc. set this automatically)
    port = int(os.environ.get("PORT", 5000))
    
    # Run the Flask app; 0.0.0.0 allows external access
    app.run(host="0.0.0.0", port=port, debug=True)
