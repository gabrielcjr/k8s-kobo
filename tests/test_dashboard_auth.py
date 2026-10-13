import pytest

def test_healthcheck(client):
    """
    Verify healthcheck endpoint /healthz returns status ok for K8s liveness/readiness probes.
    """
    res = client.get("/healthz")
    assert res.status_code == 200
    data = res.json()
    assert data.get("status") == "ok"
    assert data.get("app") == "kobo-renovame"
    assert "time" in data

def test_dashboard_unauthenticated_rejected(client):
    """
    Verify /dashboard and /admin endpoints require Basic Authentication.
    """
    for path in ["/dashboard", "/admin"]:
        res = client.get(path)
        assert res.status_code == 401
        assert "Basic realm=" in res.headers.get("www-authenticate", "")

def test_dashboard_invalid_credentials_rejected(client):
    """
    Verify invalid credentials are appropriately rejected with 401 Unauthorized.
    """
    headers = {"Authorization": "Basic d3Jvbmc6Y3JlZHM="}
    res = client.get("/dashboard", headers=headers)
    assert res.status_code == 401
    assert "Basic realm=" in res.headers.get("www-authenticate", "")

def test_dashboard_authenticated_success(client, valid_auth_headers):
    """
    Verify valid credentials grant access to dashboard, rendering metrics,
    export buttons, and submission records.
    """
    res = client.get("/dashboard", headers=valid_auth_headers)
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    html = res.text

    assert "Missionários Renova-me" in html
    assert "Total de Registros" in html or "Total de Vidas" in html or "Total" in html
    assert "/api/export/xlsx" in html
    assert "/data.csv" in html

def test_admin_alias_authenticated_success(client, valid_auth_headers):
    """
    Verify /admin alias behaves identically to /dashboard.
    """
    res = client.get("/admin", headers=valid_auth_headers)
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "Missionários Renova-me" in res.text

def test_api_dashboard_live(client, valid_auth_headers):
    """
    Verify /api/dashboard/live requires authentication and returns dynamic live data
    (total, stats, submissions, timestamp) for the real-time auto-updating dashboard.
    """
    # Unauthenticated rejected
    res_unauth = client.get("/api/dashboard/live")
    assert res_unauth.status_code == 401

    # Authenticated success
    res = client.get("/api/dashboard/live", headers=valid_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "stats" in data
    assert "submissions" in data
    assert "timestamp" in data
    assert isinstance(data["submissions"], list)

def test_dashboard_cidade_povoado_and_filters(client, valid_auth_headers):
    """
    Verify that the dashboard displays Cidade and Povoado columns,
    provides field filter dropdowns (Cidade, Povoado, Jesus, Missionário, etc.),
    and contains reactive subtotal calculation logic for top KPI cards.
    """
    res = client.get("/dashboard", headers=valid_auth_headers)
    assert res.status_code == 200
    html = res.text

    # 1. Cidade and Povoado table columns
    assert "<th>Cidade</th>" in html
    assert "<th>Povoado</th>" in html
    assert "badge-cidade" in html
    assert "badge-povoado" in html

    # 2. Filter controls
    assert 'id="filterCidade"' in html
    assert 'id="filterPovoado"' in html
    assert 'id="filterJesus"' in html
    assert 'id="filterMissionario"' in html
    assert 'id="filterGenero"' in html
    assert 'id="searchInput"' in html
    assert "Limpar Filtros" in html

    # 3. Dynamic Subtotals KPI elements
    assert 'id="kpiTotalDesc"' in html
    assert 'id="kpiTodayDesc"' in html
    assert 'id="kpiJesusDesc"' in html
    assert 'id="kpiMissionariesDesc"' in html

    # 4. Filter and subtotal reactive functions
    assert "applyFilters" in html
    assert "resetFilters" in html
    assert "populateFilterOptions" in html
    assert "Subtotal filtrado" in html


