from flask import Flask, render_template
import os

app = Flask(__name__)

@app.route("/")
def index():
    q = "Hello, Hackathon!"  # replace with your logic
    return render_template("index.html", q=q)

if __name__ == "__main__":
    # Get port from environment variable (Render sets PORT automatically)
    port = int(os.environ.get("PORT", 5000))
    # Use 0.0.0.0 so external connections can reach the app
    app.run(host="0.0.0.0", port=port)

