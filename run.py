import os

from app.main import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5050"))
    debug = os.getenv("FLASK_ENV") != "production"
    app.run(host="0.0.0.0", port=port, debug=debug)
