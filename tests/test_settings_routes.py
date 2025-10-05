import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from market_scanner.routers import settings as settings_routes
from market_scanner.routers import watchlists as watchlists_routes


@pytest.mark.asyncio
async def test_get_settings(monkeypatch):
    async def fake_profile():
        return {"weights": {"liquidity": 1.0}, "manipulation_threshold": 20, "notional": 6000}

    async def fake_watchlists():
        return [{"name": "focus", "symbols": ["BTC/USDT:USDT"], "count": 1}]

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
    async def fake_upsert(name, weights, manipulation_threshold, notional, *, session=None):
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
    assert response.json()['ok'] is True
    assert fake_upsert.called


@pytest.mark.asyncio
async def test_watchlist_post(monkeypatch):
    async def fake_upsert_watchlist(name, symbols=None):
        fake_upsert_watchlist.called = (name, symbols)
        return {"name": name, "symbols": symbols or []}

    fake_upsert_watchlist.called = None
    monkeypatch.setattr(watchlists_routes.settings_store, 'upsert_watchlist', fake_upsert_watchlist)

    app = FastAPI()
    app.include_router(watchlists_routes.router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post('/watchlists', json={"name": "focus", "symbols": ["BTC/USDT:USDT"]})
    assert response.status_code == 200
    assert fake_upsert_watchlist.called[0] == 'focus'


@pytest.mark.asyncio
async def test_watchlist_symbol_mutations(monkeypatch):
    records = {
        'added': [],
        'removed': [],
        'reordered': [],
        'deleted': None,
    }

    async def fake_add(name, symbol, position=None):
        records['added'].append((name, symbol, position))
        return {"name": name, "symbols": [symbol]}

    async def fake_remove(name, symbol):
        records['removed'].append((name, symbol))
        return {"name": name, "symbols": []}

    async def fake_reorder(name, symbols):
        records['reordered'].append((name, list(symbols)))
        return {"name": name, "symbols": list(symbols)}

    async def fake_delete(name):
        records['deleted'] = name

    monkeypatch.setattr(watchlists_routes.settings_store, 'add_symbol_to_watchlist', fake_add)
    monkeypatch.setattr(watchlists_routes.settings_store, 'remove_symbol_from_watchlist', fake_remove)
    monkeypatch.setattr(watchlists_routes.settings_store, 'reorder_watchlist', fake_reorder)
    monkeypatch.setattr(watchlists_routes.settings_store, 'delete_watchlist', fake_delete)

    app = FastAPI()
    app.include_router(watchlists_routes.router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp_add = await client.post('/watchlists/focus/symbols', json={"symbols": ["BTC"]})
        assert resp_add.status_code == 200
        resp_remove = await client.delete('/watchlists/focus/symbols/BTC')
        assert resp_remove.status_code == 200
        resp_reorder = await client.patch('/watchlists/focus', json={"symbols": ["ETH", "BTC"]})
        assert resp_reorder.status_code == 200
        resp_delete = await client.delete('/watchlists/focus')
        assert resp_delete.status_code == 200

    assert records['added'][0][1] == 'BTC'
    assert records['removed'][0][1] == 'BTC'
    assert records['reordered'][0][1] == ['ETH', 'BTC']
    assert records['deleted'] == 'focus'


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
