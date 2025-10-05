import pytest

from market_scanner.stores import settings_store


class DummySession:
    def __init__(self):
        self.statements = []
        self.committed = False
        self.flushed = False

    async def execute(self, stmt):
        self.statements.append(stmt)

    async def commit(self):
        self.committed = True

    async def flush(self):
        self.flushed = True


@pytest.mark.asyncio
async def test_upsert_user_profile_uses_postgres_insert(monkeypatch):
    session = DummySession()

    await settings_store.upsert_user_profile(
        name="default",
        weights={"liquidity": 1.0, "momentum": 0.5, "spread": 0.2},
        manipulation_threshold=25.0,
        notional=5000.0,
        session=session,
    )

    assert session.flushed is True
    assert session.committed is False
    assert len(session.statements) == 1

    upsert_stmt = session.statements[0]
    # SQLAlchemy's PostgreSQL insert exposes the `excluded` accessor.
    assert hasattr(upsert_stmt.insert, "excluded")
    assert upsert_stmt.insert.table.name == "user_profiles"
