import os
import tempfile
import pytest
from fastapi.testclient import TestClient

# Setup test environment with temporary database directory
temp_dir = tempfile.TemporaryDirectory()
os.environ["DATA_DIR"] = temp_dir.name
os.environ["KOBO_USER"] = "renovamechurch"
os.environ["KOBO_PASS"] = "Rvehonraegloria"

import sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.database import init_db
from app.main import app

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    init_db()
    yield
    temp_dir.cleanup()

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def valid_auth_headers():
    import base64
    creds = base64.b64encode(b"renovamechurch:Rvehonraegloria").decode("utf-8")
    return {"Authorization": f"Basic {creds}"}

@pytest.fixture
def sample_xml_submission():
    return """<a7FqboN3tiXKPo6hSc8MzJ id="a7FqboN3tiXKPo6hSc8MzJ" version="32 (2025-09-12 17:50:03)">
  <formhub><uuid>fe67ba249d41444a9de6eea1f809669d</uuid></formhub>
  <deviceid>collect:test-device-unit</deviceid>
  <Data>2026-10-13</Data>
  <Nome>Roberto Albuquerque</Nome>
  <Idade>45</Idade>
  <Telefone>75988112233</Telefone>
  <Genero>Masculino</Genero>
  <Recebeu_a_Jesus>Sim</Recebeu_a_Jesus>
  <Endereco_ou_referencia>Rua das Flores, 88</Endereco_ou_referencia>
  <Geolocalizador>-12.2570 -38.9640 130.0 4.5</Geolocalizador>
  <Observacoes>Contato de teste para suíte de validação</Observacoes>
  <Nome_do_Mission_rio_a>Missionário André</Nome_do_Mission_rio_a>
  <__version__>vJinrNn9dyZEpFvgvihwQW</__version__>
  <meta><instanceID>uuid:unit-test-instance-12345</instanceID></meta>
</a7FqboN3tiXKPo6hSc8MzJ>"""
