"""Entry point for the Knowledge Corpus Manager web application."""

from app import create_app

app = create_app()

if __name__ == "__main__":
    cfg = app.config["KCM"]
    app.run(
        host=cfg["server"]["host"],
        port=cfg["server"]["port"],
        debug=cfg["server"]["debug"],
    )
