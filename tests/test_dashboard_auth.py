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
    assert "/campo-missionarios.csv" in html

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

def test_dashboard_edit_and_delete_ui_elements(client, valid_auth_headers):
    """
    Verify that the dashboard displays action buttons (Editar, Excluir)
    and includes the full editing modal dialog with all required fields.
    """
    res = client.get("/dashboard", headers=valid_auth_headers)
    assert res.status_code == 200
    html = res.text

    assert "<th>Ações</th>" in html
    assert "btn-action-edit" in html
    assert "btn-action-delete" in html
    assert "editModalBackdrop" in html
    assert "edit_nome" in html
    assert "edit_cidade" in html
    assert "edit_povoado" in html
    assert "openEditModal" in html
    assert "saveEditSubmission" in html
    assert "confirmDeleteSubmission" in html

def test_dashboard_api_update_submission(client, valid_auth_headers):
    """
    Verify PUT /api/dashboard/submissions/{id} updates fields in SQLite
    and requires HTTP Basic Authentication.
    """
    # 1. Create a submission
    create_res = client.post("/api/submit", json={
        "nome": "Original Name",
        "idade": 30,
        "telefone": "75999881122",
        "genero": "Masculino",
        "recebeu_jesus": "Não",
        "missionario": "Missionário João",
        "cidade": "Cruz das Almas",
        "povoado": "Centro"
    })
    assert create_res.status_code == 200
    sub_id = create_res.json()["id"]

    # 2. Unauthenticated PUT rejected
    update_payload = {
        "nome": "Nome Modificado",
        "cidade": "Feira de Santana",
        "povoado": "Tomba",
        "recebeu_jesus": "Sim"
    }
    unauth_res = client.put(f"/api/dashboard/submissions/{sub_id}", json=update_payload)
    assert unauth_res.status_code == 401

    # 3. Authenticated PUT success
    auth_res = client.put(f"/api/dashboard/submissions/{sub_id}", json=update_payload, headers=valid_auth_headers)
    assert auth_res.status_code == 200
    data = auth_res.json()
    assert data["status"] == "success"
    assert data["submission"]["nome"] == "Nome Modificado"
    assert data["submission"]["cidade"] == "Feira de Santana"
    assert data["submission"]["povoado"] == "Tomba"
    assert data["submission"]["recebeu_jesus"] == "Sim"

    # 4. Verify GET endpoint
    get_res = client.get(f"/api/dashboard/submissions/{sub_id}", headers=valid_auth_headers)
    assert get_res.status_code == 200
    assert get_res.json()["nome"] == "Nome Modificado"

def test_dashboard_api_delete_submission(client, valid_auth_headers):
    """
    Verify DELETE /api/dashboard/submissions/{id} deletes the record from database
    and requires HTTP Basic Authentication.
    """
    # 1. Create a submission
    create_res = client.post("/api/submit", json={
        "nome": "Para Excluir",
        "idade": 30,
        "telefone": "75988776655",
        "genero": "Feminino",
        "recebeu_jesus": "Sim",
        "missionario": "Missionária Maria"
    })
    assert create_res.status_code == 200
    sub_id = create_res.json()["id"]

    # 2. Unauthenticated DELETE rejected
    unauth_res = client.delete(f"/api/dashboard/submissions/{sub_id}")
    assert unauth_res.status_code == 401

    # 3. Authenticated DELETE success
    auth_res = client.delete(f"/api/dashboard/submissions/{sub_id}", headers=valid_auth_headers)
    assert auth_res.status_code == 200
    assert auth_res.json()["status"] == "success"
    assert auth_res.json()["id"] == sub_id

    # 4. Subsequent GET and DELETE return 404
    get_res = client.get(f"/api/dashboard/submissions/{sub_id}", headers=valid_auth_headers)
    assert get_res.status_code == 404

    second_del = client.delete(f"/api/dashboard/submissions/{sub_id}", headers=valid_auth_headers)
    assert second_del.status_code == 404

def test_dashboard_filtered_export_buttons_ui(client, valid_auth_headers):
    """
    Verify dashboard contains interactive export buttons (navbar and table header)
    and JavaScript function updateExportLinks to dynamically adjust download links.
    """
    res = client.get("/dashboard", headers=valid_auth_headers)
    assert res.status_code == 200
    html = res.text

    assert 'id="btnExportXlsx"' in html
    assert 'id="btnExportCsv"' in html
    assert 'id="btnTableExportXlsx"' in html
    assert 'id="btnTableExportCsv"' in html
    assert 'function updateExportLinks' in html
    assert 'updateExportLinks(' in html


def test_30_day_auth_cookie_and_session_persistence(client, valid_auth_headers):
    """
    Verify that authenticating at /dashboard issues a 30-day HttpOnly cookie (kobo_session)
    and subsequent requests to dashboard, live polling, and exports succeed using ONLY the cookie.
    """
    # 1. Initial login with HTTP Basic
    login_res = client.get("/dashboard", headers=valid_auth_headers)
    assert login_res.status_code == 200
    assert "kobo_session" in login_res.cookies
    set_cookie = login_res.headers.get("set-cookie", "")
    assert "Max-Age=2592000" in set_cookie  # 30 days = 2,592,000s
    assert "HttpOnly" in set_cookie or "httponly" in set_cookie.lower()

    session_cookie = {"kobo_session": login_res.cookies["kobo_session"]}

    # 2. Access /dashboard with ONLY the cookie (no Authorization header)
    dash_res = client.get("/dashboard", cookies=session_cookie)
    assert dash_res.status_code == 200
    assert "Missionários Renova-me" in dash_res.text

    # 3. Access /api/dashboard/live with ONLY the cookie
    live_res = client.get("/api/dashboard/live", cookies=session_cookie)
    assert live_res.status_code == 200
    assert "total" in live_res.json()

    # 4. Access /campo-missionarios.csv with ONLY the cookie
    csv_res = client.get("/campo-missionarios.csv", cookies=session_cookie)
    assert csv_res.status_code == 200
    assert "Data,Cidade,Povoado" in csv_res.text

    # 5. Access /api/export/xlsx with ONLY the cookie
    xlsx_res = client.get("/api/export/xlsx", cookies=session_cookie)
    assert xlsx_res.status_code == 200

    # 6. Tampered cookie is rejected with 401
    bad_res = client.get("/dashboard", cookies={"kobo_session": "tampered:12345:fake"})
    assert bad_res.status_code == 401


def test_logout_clears_cookie(client, valid_auth_headers):
    """
    Verify /logout renders the session ended page, deletes kobo_session,
    and sets kobo_logged_out so subsequent requests force a fresh login prompt.
    """
    login_res = client.get("/dashboard", headers=valid_auth_headers)
    assert "kobo_session" in login_res.cookies

    # 1. /logout renders dedicated session closed screen and clears cookie
    logout_res = client.get("/logout")
    assert logout_res.status_code == 200
    assert "Sessão Encerrada" in logout_res.text
    set_cookie = logout_res.headers.get("set-cookie", "")
    assert 'kobo_session=""' in set_cookie or "Max-Age=0" in set_cookie or "max-age=0" in set_cookie.lower()
    assert "kobo_logged_out=1" in set_cookie

    # 2. Subsequent dashboard access after logout is blocked with 401 (forcing prompt)
    dash_after = client.get("/dashboard", cookies={"kobo_logged_out": "1"})
    assert dash_after.status_code == 401
    assert "Basic realm=" in dash_after.headers.get("www-authenticate", "")

    # 3. /api/logout-challenge returns 401 to drop cached browser credentials
    chal_res = client.get("/api/logout-challenge")
    assert chal_res.status_code == 401
    assert "Basic realm=" in chal_res.headers.get("www-authenticate", "")
