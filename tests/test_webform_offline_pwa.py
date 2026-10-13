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

def test_webform_dashboard_access_options(client):
    """
    Verify that the webform provides clear, visible options to access the dashboard
    across multiple strategic places: top bar, header, drawer, and success modal.
    """
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    
    # 1. Top bar button
    assert 'href="/dashboard"' in html
    assert "topDashboardBtn" in html or "dashboard-top-btn" in html
    
    # 2. Drawer footer button
    assert "drawerDashboardBtn" in html or "drawer-btn-dashboard" in html
    
    # 3. Success modal button
    assert "modalDashboardBtn" in html

def test_webform_blocks_editing_of_uploaded_records(client):
    """
    Verify that client-side logic strictly prevents editing records that have already been submitted (uploaded).
    """
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    # Verify queue list locks uploaded items
    assert "!isUploaded" in html
    assert "Bloqueado" in html or "Enviado" in html
    
    # Verify loadRecordToEdit guards against uploaded status
    assert 'item.status === "uploaded"' in html
    assert "não pode mais ser editado" in html
    
    # Verify saveAsDraft and submit guard against uploaded status
    assert "não permite alterações" in html or "não pode mais ser alterado" in html
    assert "clearFormFields" in html
