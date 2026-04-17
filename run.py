import os

from app.main import create_app
from app.config import Config

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5050"))
    app.run(host="0.0.0.0", port=port, debug=Config.FLASK_ENV == "development", use_reloader=Config.USE_RELOADER)
