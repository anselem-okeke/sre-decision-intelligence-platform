from sqlalchemy import inspect

from app.db.session import engine


def test_core_decision_tables_exist():
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    assert "incidents" in tables
    assert "signals" in tables
    assert "evidence_items" in tables
    assert "decisions" in tables
    assert "rule_evaluations" in tables
    assert "alembic_version" in tables
