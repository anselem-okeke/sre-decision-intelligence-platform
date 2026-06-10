from sqlalchemy import text

from app.db.session import engine


def clean_decision_tables() -> None:
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM rule_evaluations"))
        connection.execute(text("DELETE FROM decisions"))
        connection.execute(text("DELETE FROM evidence_items"))
        connection.execute(text("DELETE FROM signals"))
        connection.execute(text("DELETE FROM incidents"))
