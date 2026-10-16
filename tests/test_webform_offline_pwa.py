import json
import pytest
from app.database import get_submission_by_uuid

def test_webform_root_page(client):
    """
    Verify GET / renders the Enketo-style responsive webform with all form fields,
    offline draft buttons, and queue drawer.
    """
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    html = res.text
    
    assert "Missionários Renova-me" in html
    assert "Banner_renovam_vermelho.png" in html
    
    # Check form inputs and identifiers
    assert 'name="Nome"' in html or 'id="f_nome"' in html
    assert 'name="Idade"' in html or 'id="f_idade"' in html
    assert 'name="Telefone"' in html or 'id="f_telefone"' in html
    assert 'name="Genero"' in html or 'id="f_genero"' in html
    assert 'name="Recebeu_a_Jesus"' in html or 'id="f_recebeu"' in html
    assert 'name="Nome_do_Mission_rio_a"' in html or 'id="f_missionario"' in html
    
    # Check offline & draft elements
    assert "Salvar Rascunho" in html
    assert "Finalizar e Enviar" in html
    assert "queueDrawer" in html or "drawer" in html
    assert "offline" in html.lower()

def test_enketo_url_slug_compatibility(client):
    """
    Verify /x/PY2hbkKi renders the webform identically to Enketo KoBoToolbox URL format.
    """
    res = client.get("/x/PY2hbkKi")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "Missionários Renova-me" in res.text

    # Custom slug compatibility
    res_custom = client.get("/x/customSlug123")
    assert res_custom.status_code == 200
    assert "Missionários Renova-me" in res_custom.text

def test_service_worker_endpoints(client):
    """
    Verify Service Worker endpoints /sw.js and /x/offline-app-worker.js
    provide caching and offline PWA functionality with proper headers.
    """
    for endpoint in ["/sw.js", "/x/offline-app-worker.js"]:
        res = client.get(endpoint)
        assert res.status_code == 200, f"SW endpoint {endpoint} failed"
        assert "application/javascript" in res.headers["content-type"]
        assert res.headers.get("service-worker-allowed") == "/"
        assert "no-cache" in res.headers.get("cache-control", "")
        
        content = res.text
        assert "CACHE_NAME" in content or "caches.open" in content
        assert "PY2hbkKi" in content
        assert "fetch" in content

def test_manifest_endpoint(client):
    """
    Verify /manifest.json conforms to PWA Web App Manifest standard.
    """
    res = client.get("/manifest.json")
    assert res.status_code == 200
    assert "manifest+json" in res.headers["content-type"]
    data = res.json()
    assert data["name"] == "Missionários Renova-me"
    assert data["short_name"] == "Renova-me"
    assert data["display"] == "standalone"
    assert "/x/PY2hbkKi" in data["start_url"]
    assert "icons" in data
    assert len(data["icons"]) >= 1

def test_api_submit_success(client):
    """
    Verify POST /api/submit successfully records web form entries into database
    and marks source as 'web'.
    """
    payload = {
        "data_date": "2026-10-13",
        "nome": "Maria Aparecida",
        "idade": 42,
        "telefone": "75988223344",
        "genero": "Feminino",
        "recebeu_jesus": "Sim",
        "endereco": "Avenida Central, 500",
        "geopoint": "-12.2570 -38.9640 110.0 3.5",
        "observacoes": "Aceitou a oração e pediu visita",
        "missionario": "Missionária Débora"
    }
    res = client.post("/api/submit", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "id" in data
    assert "uuid" in data
    
    # Verify in DB
    record = get_submission_by_uuid(data["uuid"])
    assert record is not None
    assert record["nome"] == "Maria Aparecida"
    assert record["idade"] == 42
    assert record["source"] == "web"
    assert record["device_id"] == "web-browser"
    assert record["latitude"] == pytest.approx(-12.2570, rel=1e-4)
    assert record["longitude"] == pytest.approx(-38.9640, rel=1e-4)

def test_api_submit_validation_missing_required(client):
    """
    Verify POST /api/submit validates required fields (e.g. nome, telefone, etc.).
    """
    # Missing required field 'nome'
    payload = {
        "telefone": "75999999999",
        "genero": "Feminino",
        "recebeu_jesus": "Sim",
        "missionario": "Missionário João"
    }
    res = client.post("/api/submit", json=payload)
    assert res.status_code == 422  # FastAPI validation error

def test_api_submit_defaults_data_date(client):
    """
    Verify POST /api/submit auto-generates data_date if omitted.
    """
    payload = {
        "nome": "Pedro Henrique",
        "idade": 30,
        "telefone": "75977665544",
        "genero": "Masculino",
        "recebeu_jesus": "evangelico",
        "missionario": "Missionário Lucas"
    }
    res = client.post("/api/submit", json=payload)
    assert res.status_code == 200
    data = res.json()
    record = get_submission_by_uuid(data["uuid"])
    assert record is not None
    assert record["data_date"] is not None
    assert len(record["data_date"]) == 10  # YYYY-MM-DD

def test_webform_dashboard_and_backup_links_removed(client):
    """
    Verify that the webform has NO dashboard links or local backup export anywhere,
    ensuring standard missionary users cannot access admin/dashboard or dump data.
    """
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    
    # 1. No dashboard or admin links
    assert 'href="/dashboard"' not in html
    assert 'href="/admin"' not in html
    assert "topDashboardBtn" not in html
    assert "drawerDashboardBtn" not in html
    assert "modalDashboardBtn" not in html
    assert "dashboard-top-btn" not in html
    assert "Ver Painel" not in html
    
    # 2. No local backup export button
    assert "exportBackupJson" not in html
    assert "Exportar Backup" not in html

def test_webform_submitted_records_purged_for_security(client):
    """
    Verify that once submitted, records are purged from device storage for information security.
    Only drafts and queued offline records are retained.
    """
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    # Storage filter only keeps draft and queued
    assert 'r.status === "draft" || r.status === "queued"' in html
    
    # Successful submission purges record from client storage
    assert "remainingRecords = getRecords().filter(r => r.id !== recordId)" in html
    assert "deleteRecord(id)" in html
    
    # Security message in queue drawer
    assert "segurança da informação" in html




def test_api_submit_server_side_validation_mirrors_xform(client):
    """
    /api/submit must enforce the same rules as Missionarios_Renovame.xml
    (telefone 11 dígitos, idade obrigatória, opções válidas), not just the browser.
    """
    base = {
        "nome": "Validação Teste",
        "idade": 30,
        "telefone": "75988887777",
        "genero": "Feminino",
        "recebeu_jesus": "Sim",
        "missionario": "Missionário Validador",
    }
    assert client.post("/api/submit", json={**base, "telefone": "12345"}).status_code == 422
    assert client.post("/api/submit", json={**base, "idade": None}).status_code == 422
    assert client.post("/api/submit", json={**base, "genero": "Outro"}).status_code == 422
    assert client.post("/api/submit", json={**base, "recebeu_jesus": "Talvez"}).status_code == 422
    assert client.post("/api/submit", json={**base, "missionario": "   "}).status_code == 422

    # Formatted phone is accepted and normalized to digits
    ok = client.post("/api/submit", json={**base, "telefone": "(75) 98888-7777"})
    assert ok.status_code == 200
    record = get_submission_by_uuid(ok.json()["uuid"])
    assert record["telefone"] == "75988887777"

    # GPS is optional (web form sends a placeholder when GPS is denied)
    assert client.post("/api/submit", json={**base, "geopoint": None}).status_code == 200
