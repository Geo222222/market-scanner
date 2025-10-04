import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from market_scanner.routers import settings as settings_routes


@pytest.mark.asyncio
async def test_get_settings(monkeypatch):
    async def fake_profile():
        return {"weights": {"liquidity": 1.0}, "manipulation_threshold": 20, "notional": 6000}

    async def fake_watchlists():
        return [{"name": "focus", "symbols": ["BTC/USDT:USDT"]}]

    monkeypatch.setattr(settings_routes.settings_store, 'get_user_profile', lambda name='default': fake_profile())
    monkeypatch.setattr(settings_routes.settings_store, 'list_watchlists', lambda: fake_watchlists())

    app = FastAPI()
    app.include_router(settings_routes.router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get('/settings')
    assert response.status_code == 200
    data = response.json()
    assert data['weights']['liquidity'] == 1.0


@pytest.mark.asyncio
async def test_post_settings(monkeypatch):
    async def fake_upsert(name, weights, manipulation_threshold, notional):
        fake_upsert.called = True

    fake_upsert.called = False

    monkeypatch.setattr(settings_routes.settings_store, 'upsert_user_profile', fake_upsert)
    monkeypatch.setattr(settings_routes, 'set_profile_override', lambda profile, override: None)
    monkeypatch.setattr(settings_routes, 'set_manipulation_threshold', lambda value: None)
    monkeypatch.setattr(settings_routes, 'set_notional_override', lambda value: None)

    app = FastAPI()
    app.include_router(settings_routes.router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post('/settings', json={
            'liquidity_weight': 1.5,
            'momentum_weight': 0.5,
            'spread_penalty': 2.0,
            'manipulation_threshold': 30,
            'notional': 7000,
        })
    assert response.status_code == 200
    assert fake_upsert.called


@pytest.mark.asyncio
async def test_watchlist_post(monkeypatch):
    async def fake_upsert_watchlist(name, symbols=None):
        fake_upsert_watchlist.called = (name, symbols)
        return {"name": name, "symbols": symbols or []}

    fake_upsert_watchlist.called = None
    from market_scanner.routers import watchlists as watchlists_routes
    monkeypatch.setattr(watchlists_routes.settings_store, 'upsert_watchlist', fake_upsert_watchlist)

    app = FastAPI()
    app.include_router(watchlists_routes.router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post('/watchlists', json={"name": "focus", "symbols": ["BTC/USDT:USDT"]})
    assert response.status_code == 200
    assert fake_upsert_watchlist.called[0] == 'focus'


@pytest.mark.asyncio
async def test_profiles_apply(monkeypatch):
    from market_scanner.routers import profiles as profiles_router

    async def fake_get(name):
        return {"name": name, "weights": {"edges": {"liquidity": 2.0}}}

    async def fake_list():
        return ['session']

    monkeypatch.setattr(profiles_router.settings_store, 'get_profile_preset', fake_get)
    monkeypatch.setattr(profiles_router.settings_store, 'list_profile_presets', fake_list)
    applied = {}
    monkeypatch.setattr(profiles_router, 'set_profile_override', lambda profile, weights: applied.setdefault('weights', weights))

    app = FastAPI()
    app.include_router(profiles_router.router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        response = await client.post('/profiles/apply', params={'name': 'session'})
    assert response.status_code == 200
    assert applied['weights']['edges']['liquidity'] == 2.0
