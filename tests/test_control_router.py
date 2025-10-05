import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from market_scanner.routers import control as control_router


@pytest.mark.asyncio
async def test_control_state(monkeypatch):
    monkeypatch.setattr(control_router, 'get_control_state', lambda: {'paused': False})

    app = FastAPI()
    app.include_router(control_router.router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        response = await client.get('/control/state')
    assert response.status_code == 200
    assert response.json()['paused'] is False


@pytest.mark.asyncio
async def test_force_scan(monkeypatch):
    async def fake_force(actor: str = 'api', reason=None):
        return {'queued': True, 'actor': actor, 'reason': reason}

    monkeypatch.setattr(control_router, 'request_force_scan', fake_force)

    app = FastAPI()
    app.include_router(control_router.router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        response = await client.post('/control/force-scan', json={'reason': 'manual'})
    assert response.status_code == 200
    assert response.json()['queued'] is True


@pytest.mark.asyncio
async def test_force_scan_conflict(monkeypatch):
    async def fake_force(actor: str = 'api', reason=None):
        return {'queued': False, 'reason': 'paused'}

    monkeypatch.setattr(control_router, 'request_force_scan', fake_force)

    app = FastAPI()
    app.include_router(control_router.router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        response = await client.post('/control/force-scan', json={})
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_pause_resume(monkeypatch):
    async def fake_pause(actor: str = 'api', reason=None):
        return {'paused': True}

    async def fake_resume(actor: str = 'api', reason=None):
        return {'paused': False}

    monkeypatch.setattr(control_router, 'pause_scanner', fake_pause)
    monkeypatch.setattr(control_router, 'resume_scanner', fake_resume)

    app = FastAPI()
    app.include_router(control_router.router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        pause_resp = await client.post('/control/pause', json={'reason': 'manual'})
        resume_resp = await client.post('/control/resume', json={'reason': 'manual'})
    assert pause_resp.status_code == 200
    assert pause_resp.json()['paused'] is True
    assert resume_resp.json()['paused'] is False


@pytest.mark.asyncio
async def test_breaker(monkeypatch):
    def fake_breaker(state: str, actor: str = 'api', reason=None):
        return {'manual_state': state, 'last_reason': reason}

    monkeypatch.setattr(control_router, 'set_manual_breaker', fake_breaker)

    app = FastAPI()
    app.include_router(control_router.router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as client:
        response = await client.post('/control/breaker', json={'state': 'open', 'reason': 'latency'})
    assert response.status_code == 200
    assert response.json()['manual_state'] == 'open'
