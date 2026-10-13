import csv
import io
import openpyxl
import pytest
from app.database import insert_submission

@pytest.fixture(autouse=True)
def seed_test_submission():
    """Ensure at least one standard test record exists in the database."""
    insert_submission(
        uuid="test-uuid-google-sheets-1",
        form_id="a7FqboN3tiXKPo6hSc8MzJ",
        version="32 (2025-09-12 17:50:03)",
        data_date="2026-10-13",
        nome="Carlos Silva",
        idade=34,
        telefone="75999887766",
        genero="Masculino",
        recebeu_jesus="Sim",
        endereco="Rua Principal, 100",
        geopoint="-12.2570 -38.9640 120.0 5.0",
        observacoes="Interessado nos estudos bíblicos",
        missionario="Missionário Teste",
        device_id="collect:seed-test",
        submitted_by="renovamechurch",
        source="kobo_collect"
    )

def test_data_export_endpoints_unauthenticated_rejected(client):
    """
    Por segurança dos dados, a API aberta foi removida.
    Todas as requisições não autenticadas a endpoints de exportação de dados
    devem ser rejeitadas com HTTP 401 Unauthorized.
    """
    endpoints = [
        "/data.csv",
        "/api/export/csv",
        "/api/v2/assets/a7FqboN3tiXKPo6hSc8MzJ/data.csv",
        "/api/v2/assets/a7FqboN3tiXKPo6hSc8MzJ/data.csv/",
        "/api/v2/assets/a7FqboN3tiXKPo6hSc8MzJ/export-settings/esjanp2i9bM7zAYduBVtzXe/data.csv",
        "/api/v1/data/a7FqboN3tiXKPo6hSc8MzJ.csv",
        "/campo-missionarios.csv",
        "/sheets.csv",
        "/api/export/campo-missionarios.csv",
        "/data.json",
        "/api/v2/assets/a7FqboN3tiXKPo6hSc8MzJ/data.json",
        "/api/v1/data/a7FqboN3tiXKPo6hSc8MzJ.json",
        "/api/export/geojson",
        "/api/export/xlsx",
        "/api/dashboard/copy-tsv",
    ]
    for url in endpoints:
        res = client.get(url)
        assert res.status_code == 401, f"GET {url} should have failed with 401, got {res.status_code}"
        assert "Basic realm=" in res.headers.get("www-authenticate", "")

        head_res = client.head(url)
        assert head_res.status_code == 401, f"HEAD {url} should have failed with 401, got {head_res.status_code}"

def test_csv_structure_raw_field_names(client, valid_auth_headers):
    """
    Verify exact KoBoToolbox field structure when authenticated.
    """
    res = client.get("/api/v2/assets/a7FqboN3tiXKPo6hSc8MzJ/data.csv", headers=valid_auth_headers)
    assert res.status_code == 200
    reader = csv.reader(io.StringIO(res.text))
    rows = list(reader)
    assert len(rows) >= 2  # Header + at least 1 record
    
    header = rows[0]
    expected_columns = [
        "start", "end", "today", "deviceid", "Data", "Nome", "Idade",
        "Telefone", "Genero", "Recebeu_a_Jesus", "Endereco_ou_referencia",
        "Geolocalizador", "_Geolocalizador_latitude", "_Geolocalizador_longitude",
        "_Geolocalizador_altitude", "_Geolocalizador_precision", "Observacoes",
        "Nome_do_Mission_rio_a", "__version__", "_id", "_uuid", "_submission_time",
        "_validation_status", "_notes", "_status", "_submitted_by", "_tags", "_index"
    ]
    for col in expected_columns:
        assert col in header, f"Column {col} missing in CSV header"

    # Find row with Carlos Silva
    carlos_row = None
    for r in rows[1:]:
        if "Carlos Silva" in r:
            carlos_row = r
            break
    assert carlos_row is not None
    nome_idx = header.index("Nome")
    tel_idx = header.index("Telefone")
    lat_idx = header.index("_Geolocalizador_latitude")
    lon_idx = header.index("_Geolocalizador_longitude")
    
    assert carlos_row[nome_idx] == "Carlos Silva"
    assert carlos_row[tel_idx] == "75999887766"
    assert carlos_row[lat_idx] == "-12.257"
    assert carlos_row[lon_idx] == "-38.964"

def test_csv_structure_with_human_labels(client, valid_auth_headers):
    """
    Verify ?labels=true or ?lang=pt produces human-readable headers when authenticated.
    """
    res = client.get("/data.csv?labels=true", headers=valid_auth_headers)
    assert res.status_code == 200
    reader = csv.reader(io.StringIO(res.text))
    rows = list(reader)
    header = rows[0]
    
    expected_labels = [
        "Data", "Nome", "Idade", "Telefone", "Gênero", "Recebeu Jesus?",
        "Endereço ou referência", "Geolocalizador", "Observações",
        "Nome do Missionário(a)", "_id", "_uuid", "_origem"
    ]
    for lbl in expected_labels:
        assert lbl in header, f"Human label {lbl} missing in CSV header"

def test_kobo_json_api_v2_endpoints(client, valid_auth_headers):
    """
    Verify KoBoToolbox v2 JSON endpoints return exact pagination and result schema when authenticated.
    """
    json_endpoints = [
        "/data.json",
        "/api/v2/assets/a7FqboN3tiXKPo6hSc8MzJ/data.json",
        "/api/v2/assets/a7FqboN3tiXKPo6hSc8MzJ/data",
        "/api/v2/assets/a7FqboN3tiXKPo6hSc8MzJ/data/",
        "/api/v1/data/a7FqboN3tiXKPo6hSc8MzJ.json"
    ]
    for url in json_endpoints:
        res = client.get(url, headers=valid_auth_headers)
        assert res.status_code == 200, f"Endpoint {url} failed with status {res.status_code}"
        data = res.json()
        assert "count" in data
        assert "results" in data
        assert isinstance(data["results"], list)
        assert data["count"] >= 1

        first = data["results"][0]
        assert "_id" in first
        assert "formhub/uuid" in first
        assert "meta/instanceID" in first
        assert "_xform_id_string" in first

def test_kobo_json_api_v1_array_endpoint(client, valid_auth_headers):
    """
    KoBo API v1 data endpoint returns raw array directly when authenticated.
    """
    res = client.get("/api/v1/data/a7FqboN3tiXKPo6hSc8MzJ", headers=valid_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1

def test_kobo_api_v2_asset_metadata(client):
    """
    Verify /api/v2/assets/{id} returns asset specification and form information.
    """
    res = client.get("/api/v2/assets/a7FqboN3tiXKPo6hSc8MzJ")
    assert res.status_code == 200
    data = res.json()
    assert data.get("uid") == "a7FqboN3tiXKPo6hSc8MzJ" or "Missionários" in data.get("name", "")

def test_kobo_api_v2_export_settings(client):
    """
    Verify /api/v2/assets/{id}/export-settings returns export configurations with CSV url.
    """
    res = client.get("/api/v2/assets/a7FqboN3tiXKPo6hSc8MzJ/export-settings")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["uid"] == "esjanp2i9bM7zAYduBVtzXe"
    assert "data_url_csv" in data[0]

def test_kobo_api_v1_forms_list(client):
    """
    Verify /api/v1/forms lists the active form.
    """
    res = client.get("/api/v1/forms")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["id_string"] == "a7FqboN3tiXKPo6hSc8MzJ"

def test_geojson_export(client, valid_auth_headers):
    """
    Verify GeoJSON endpoint produces valid RFC 7946 FeatureCollection when authenticated.
    """
    res = client.get("/api/export/geojson", headers=valid_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "FeatureCollection"
    assert "features" in data
    assert len(data["features"]) >= 1

    feature = data["features"][0]
    assert feature["type"] == "Feature"
    assert feature["geometry"]["type"] == "Point"
    coords = feature["geometry"]["coordinates"]
    assert len(coords) == 2
    assert -45 < coords[0] < -30
    assert -15 < coords[1] < -5
    assert "nome" in feature["properties"]

def test_excel_export_behavior(client, valid_auth_headers):
    """
    Verify Excel (.xlsx) export rejects invalid or missing credentials with 401,
    and returns valid XLSX binary when authenticated.
    """
    # Bad credentials must be rejected with 401
    bad_res = client.get("/api/export/xlsx", headers={"Authorization": "Basic d3Jvbmc6Y3JlZHM="})
    assert bad_res.status_code == 401

    # Unauthenticated request rejected with 401
    no_auth_res = client.get("/api/export/xlsx")
    assert no_auth_res.status_code == 401

    # Authorized request returns 200 and valid XLSX binary
    res = client.get("/api/export/xlsx", headers=valid_auth_headers)
    assert res.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in res.headers["content-type"]
    
    wb = openpyxl.load_workbook(io.BytesIO(res.content))
    assert "Missionários Renova-me" in wb.sheetnames
    ws = wb["Missionários Renova-me"]
    assert ws.max_row >= 2
    header_vals = [cell.value for cell in ws[1]]
    assert len(header_vals) == 16
    assert header_vals[0] == "Data"
    assert header_vals[1] == "Cidade"
    assert header_vals[2] == "Povoado"
    assert header_vals[3] == "Nome"
    assert header_vals[4] == "Idade"
    assert header_vals[5] == "Telefone"
    assert header_vals[6] == "Whatsapp"
    assert header_vals[7] == "Gênero"
    assert header_vals[8] is None or header_vals[8] == ""  # Coluna I vazia (sem família)
    assert header_vals[9] == "Recebeu a Jesus?"
    assert header_vals[10] is None or header_vals[10] == ""  # Coluna K vazia (sem bíblia doada)
    assert header_vals[11] == "Endereço ou referência"
    assert header_vals[12] == "Observações"
    assert header_vals[13] == "GeoLocalizador"
    assert header_vals[14] == "Localizador"
    assert header_vals[15] == "Missionário(a)"

    row2_vals = [cell.value for cell in ws[2]]
    assert len(row2_vals) == 16
    assert "F2" in str(row2_vals[6])
    assert "N2" in str(row2_vals[14])

def test_campo_missionarios_csv_structure(client, valid_auth_headers):
    """
    Verify /campo-missionarios.csv returns the exact 16 columns A..P and exact formulas
    for WhatsApp and Mapa requested by the user.
    """
    res = client.get("/campo-missionarios.csv?start_row=510", headers=valid_auth_headers)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    
    rows = list(csv.reader(io.StringIO(res.text)))
    assert len(rows) >= 2
    header = rows[0]
    assert len(header) == 16
    assert header[0] == "Data"
    assert header[1] == "Cidade"
    assert header[2] == "Povoado"
    assert header[3] == "Nome"
    assert header[4] == "Idade"
    assert header[5] == "Telefone"
    assert header[6] == "Whatsapp"
    assert header[7] == "Gênero"
    assert header[9] == "Recebeu a Jesus?"
    assert header[11] == "Endereço ou referência"
    assert header[12] == "Observações"
    assert header[14] == "Localizador"
    assert header[15] == "Missionário(a)"

    # Row 1 check (Carlos Silva at row 510)
    carlos_row = None
    for r in rows[1:]:
        if "Carlos Silva" in r:
            carlos_row = r
            break
    assert carlos_row is not None
    assert carlos_row[0] == "10/2026"  # Month/Year format
    assert carlos_row[1] == "Cruz das Almas"
    assert carlos_row[2] == "Centro"
    assert carlos_row[3] == "Carlos Silva"
    assert carlos_row[4] == "34"
    assert carlos_row[5] == "75999887766"

    # Exact WhatsApp formula check
    expected_wa_formula = '=IF(ISBLANK(F510); ""; IF(F510 = 0; "Telefone não informado"; HYPERLINK("https://wa.me/55" & F510; "Chamar no WhatsApp")))'
    assert carlos_row[6] == expected_wa_formula

    assert carlos_row[7] == "Masculino"
    assert carlos_row[9] == "Sim"
    assert carlos_row[11] == "Rua Principal, 100"
    assert carlos_row[12] == "Interessado nos estudos bíblicos"

    # Geolocalizador in N format [-12.257,-38.964]
    assert carlos_row[13] == "[-12.257,-38.964]"

    # Exact Mapa formula check
    expected_map_formula = (
        '=IF(ISBLANK(N510); ""; IF(N510 = "[NULL,NULL]"; "Localização não capturada";'
        ' IF(N510 = "[0.1,0.1]"; "Localização não capturada";'
        ' IF(N510 = "[1,1]"; "Localização não capturada";'
        ' IF(N510 = "[1,2]"; "Localização não capturada";'
        ' HYPERLINK("https://www.google.com/maps?q=" & REGEXEXTRACT(N510; "-?\\d+\\.\\d+,-?\\d+\\.\\d+"); "Ver no mapa"))))))'
    )
    assert carlos_row[14] == expected_map_formula
    assert carlos_row[15] == "Missionário Teste"

def test_campo_missionarios_custom_cidade_povoado_and_layout(client, valid_auth_headers):
    """
    Verify customizing Cidade, Povoado, and row index.
    """
    url = "/campo-missionarios.csv?cidade=Feira+de+Santana&povoado=Humildes&start_row=600"
    res = client.get(url, headers=valid_auth_headers)
    assert res.status_code == 200
    rows = list(csv.reader(io.StringIO(res.text)))
    header = rows[0]
    assert len(header) == 16

    carlos_row = None
    for r in rows[1:]:
        if "Carlos Silva" in r:
            carlos_row = r
            break
    assert carlos_row is not None
    assert carlos_row[1] == "Feira de Santana"
    assert carlos_row[2] == "Humildes"
    # Row 600 formulas
    assert "F600" in carlos_row[6]
    assert "N600" in carlos_row[14]

def test_copy_tsv_endpoint(client, valid_auth_headers):
    """
    Verify the /api/dashboard/copy-tsv endpoint generates TSV content suitable for pasting
    directly into Google Sheets.
    """
    res = client.get("/api/dashboard/copy-tsv?start_row=510", headers=valid_auth_headers)
    assert res.status_code == 200
    assert "text/tab-separated-values" in res.headers["content-type"]
    
    text = res.text
    lines = text.strip().split("\n")
    assert len(lines) >= 1
    
    first_cols = lines[0].split("\t")
    assert len(first_cols) == 16
    assert "10/2026" in first_cols[0]
    assert "Carlos Silva" in first_cols[3]
    assert "75999887766" in first_cols[5]
    assert '=IF(ISBLANK(F510); ""; IF(F510 = 0; "Telefone não informado"; HYPERLINK("https://wa.me/55" & F510; "Chamar no WhatsApp")))' in first_cols[6]
    assert "[-12.257,-38.964]" in first_cols[13]
    assert 'HYPERLINK("https://www.google.com/maps?q=" & REGEXEXTRACT(N510; "-?\\d+\\.\\d+,-?\\d+\\.\\d+"); "Ver no mapa")' in first_cols[14]

def test_aggregated_action_metadata_without_form_fields(client, valid_auth_headers):
    """
    Verify that Cidade and Povoado are aggregated without being questions in the form:
    1. Set active action via admin endpoint
    2. Submit form payload without cidade/povoado -> inherits active action
    3. Submit form payload with action context -> records specific action
    4. Query /campo-missionarios.csv with and without filtering
    """
    # 1. Set active action
    res_set = client.post(
        "/api/admin/set-active-action",
        json={"cidade": "Santo Antônio de Jesus", "povoado": "São Benedito"},
        headers=valid_auth_headers
    )
    assert res_set.status_code == 200
    assert res_set.json()["active_cidade"] == "Santo Antônio de Jesus"
    assert res_set.json()["active_povoado"] == "São Benedito"

    # 2. Submit form without explicit cidade/povoado
    sub1 = client.post("/api/submit", json={
        "nome": "Irmão Teste Agregado",
        "idade": 40,
        "telefone": "75988776655",
        "genero": "Masculino",
        "recebeu_jesus": "Sim",
        "endereco": "Praça Central",
        "geopoint": "-12.96 38.51 0.0 0.0",
        "observacoes": "Coletado na nova ação",
        "missionario": "Pr. Gabriel"
    })
    assert sub1.status_code == 200

    # 3. Submit form with specific campaign context
    sub2 = client.post("/api/submit", json={
        "nome": "Irmã Maria Campanha",
        "idade": 35,
        "telefone": "75977665544",
        "genero": "Feminino",
        "recebeu_jesus": "Sim",
        "missionario": "Missionária Débora",
        "cidade": "Valença",
        "povoado": "Guaibim"
    })
    assert sub2.status_code == 200

    # 4. Check CSV output
    res_csv = client.get("/campo-missionarios.csv", headers=valid_auth_headers)
    assert res_csv.status_code == 200
    rows = list(csv.reader(io.StringIO(res_csv.text)))
    
    # Sub1 should have inherited active action
    sub1_row = next(r for r in rows if "Irmão Teste Agregado" in r)
    assert sub1_row[1] == "Santo Antônio de Jesus"
    assert sub1_row[2] == "São Benedito"

    # Sub2 should have its specific action
    sub2_row = next(r for r in rows if "Irmã Maria Campanha" in r)
    assert sub2_row[1] == "Valença"
    assert sub2_row[2] == "Guaibim"

    # 5. Check filtered CSV output for Valença
    res_valenca = client.get("/campo-missionarios.csv?cidade=Valença", headers=valid_auth_headers)
    assert res_valenca.status_code == 200
    rows_valenca = list(csv.reader(io.StringIO(res_valenca.text)))
    valenca_names = [r[3] for r in rows_valenca[1:]]
    assert "Irmã Maria Campanha" in valenca_names
    assert "Irmão Teste Agregado" not in valenca_names

def test_export_xlsx_filtered_by_cidade(client, valid_auth_headers):
    """
    Verify /api/export/xlsx correctly filters records by cidade and reflects active filters.
    """
    # Create two records in different cities
    insert_submission(
        uuid="uuid-xlsx-filter-ilheus-1",
        form_id="a7FqboN3tiXKPo6hSc8MzJ",
        version="32",
        data_date="2026-10-13",
        nome="Missionário Ilhéus Teste",
        idade=29,
        telefone="73988001122",
        genero="Masculino",
        recebeu_jesus="Sim",
        endereco="Avenida Beira Mar",
        geopoint="-14.79 -39.04 10.0 5.0",
        observacoes="Cidade Ilhéus",
        missionario="Pr. Lucas",
        device_id="collect:test-ilheus",
        cidade="Ilhéus",
        povoado="Pontal"
    )
    insert_submission(
        uuid="uuid-xlsx-filter-itabuna-1",
        form_id="a7FqboN3tiXKPo6hSc8MzJ",
        version="32",
        data_date="2026-10-13",
        nome="Missionário Itabuna Teste",
        idade=33,
        telefone="73999112233",
        genero="Masculino",
        recebeu_jesus="Sim",
        endereco="Centro",
        geopoint="-14.80 -39.27 10.0 5.0",
        observacoes="Cidade Itabuna",
        missionario="Pr. Marcos",
        device_id="collect:test-itabuna",
        cidade="Itabuna",
        povoado="São Caetano"
    )

    # 1. Export Excel filtered for Ilhéus
    res_ilheus = client.get("/api/export/xlsx?cidade=Ilhéus", headers=valid_auth_headers)
    assert res_ilheus.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in res_ilheus.headers["content-type"]
    assert "Ilheus" in res_ilheus.headers["content-disposition"]

    wb_ilheus = openpyxl.load_workbook(io.BytesIO(res_ilheus.content))
    ws_ilheus = wb_ilheus["Missionários Renova-me"]
    header = [cell.value for cell in ws_ilheus[1]]
    assert "Cidade" in header
    assert "Povoado" in header
    assert "Nome" in header

    nome_col_idx = header.index("Nome") + 1
    cidade_col_idx = header.index("Cidade") + 1
    
    ilheus_names = [ws_ilheus.cell(r, nome_col_idx).value for r in range(2, ws_ilheus.max_row + 1)]
    ilheus_cities = [ws_ilheus.cell(r, cidade_col_idx).value for r in range(2, ws_ilheus.max_row + 1)]

    assert "Missionário Ilhéus Teste" in ilheus_names
    assert "Missionário Itabuna Teste" not in ilheus_names
    assert all(c == "Ilhéus" for c in ilheus_cities if c)

    # 2. Export Excel filtered for Itabuna
    res_itabuna = client.get("/api/export/xlsx?cidade=Itabuna", headers=valid_auth_headers)
    assert res_itabuna.status_code == 200
    assert "Itabuna" in res_itabuna.headers["content-disposition"]

    wb_itabuna = openpyxl.load_workbook(io.BytesIO(res_itabuna.content))
    ws_itabuna = wb_itabuna["Missionários Renova-me"]
    itabuna_names = [ws_itabuna.cell(r, nome_col_idx).value for r in range(2, ws_itabuna.max_row + 1)]

    assert "Missionário Itabuna Teste" in itabuna_names
    assert "Missionário Ilhéus Teste" not in itabuna_names

def test_export_csv_filtered_by_cidade(client, valid_auth_headers):
    """
    Verify /data.csv and /api/export/csv correctly filter records by cidade.
    """
    # 1. Filtered data.csv (standard format)
    res = client.get("/data.csv?cidade=Ilhéus", headers=valid_auth_headers)
    assert res.status_code == 200
    assert "Ilheus" in res.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(res.text)))
    assert len(rows) >= 2
    header = rows[0]
    nome_idx = header.index("Nome")
    names = [r[nome_idx] for r in rows[1:]]

    assert "Missionário Ilhéus Teste" in names
    assert "Missionário Itabuna Teste" not in names

    # 2. Filtered data.csv with labels
    res_labels = client.get("/data.csv?cidade=Itabuna&labels=true", headers=valid_auth_headers)
    assert res_labels.status_code == 200
    assert "Itabuna" in res_labels.headers["content-disposition"]
    rows_lbl = list(csv.reader(io.StringIO(res_labels.text)))
    header_lbl = rows_lbl[0]
    assert "Cidade" in header_lbl
    assert "Povoado" in header_lbl
    nome_lbl_idx = header_lbl.index("Nome")
    names_lbl = [r[nome_lbl_idx] for r in rows_lbl[1:]]

    assert "Missionário Itabuna Teste" in names_lbl
    assert "Missionário Ilhéus Teste" not in names_lbl


def test_exact_16_columns_export_without_familia_and_biblia_doada(client, valid_auth_headers):
    """
    Verify exact 16 columns A..P in XLSX and CSV export:
    - No familia or biblia_doada (columns I and K are empty)
    - Column G: WhatsApp formula referencing F{row}
    - Column N: GeoLocalizador format
    - Column O: Mapa formula referencing N{row}
    """
    # 1. Insert test submission with geopoint
    client.post("/api/submit", json={
        "nome": "Jaqueline Teste 16 Cols",
        "idade": 25,
        "telefone": "75988466680",
        "genero": "Feminino",
        "recebeu_jesus": "Sim",
        "endereco": "7 de setembro",
        "geopoint": "-12.301113 -38.6409991 112.8 8.3",
        "observacoes": "Teste 16 colunas",
        "missionario": "Missionário Jaqueline",
        "cidade": "Teodoro Sampaio",
        "povoado": "Sede",
        "data_date": "2025-07-15"
    })

    # 2. Check XLSX export
    res_xlsx = client.get("/api/export/xlsx?search=Jaqueline+Teste+16+Cols", headers=valid_auth_headers)
    assert res_xlsx.status_code == 200
    wb = openpyxl.load_workbook(io.BytesIO(res_xlsx.content))
    ws = wb.active
    assert ws.max_row >= 2

    # Headers verification
    headers = [cell.value for cell in ws[1]]
    assert len(headers) == 16
    expected_headers = [
        "Data", "Cidade", "Povoado", "Nome", "Idade", "Telefone", "Whatsapp",
        "Gênero", None, "Recebeu a Jesus?", None, "Endereço ou referência",
        "Observações", "GeoLocalizador", "Localizador", "Missionário(a)"
    ]
    for idx, exp in enumerate(expected_headers):
        if exp is None:
            assert headers[idx] is None or headers[idx] == ""
        else:
            assert headers[idx] == exp

    # Row 2 data verification (first data row)
    row2 = [cell.value for cell in ws[2]]
    assert row2[0] == "07/2025"  # MM/YYYY
    assert row2[1] == "Teodoro Sampaio"
    assert row2[2] == "Sede"
    assert row2[3] == "Jaqueline Teste 16 Cols"
    assert row2[4] == 25
    assert row2[5] == "75988466680"
    # WhatsApp formula on column G referencing F2
    assert '=IF(ISBLANK(F2); ""; IF(F2 = 0; "Telefone não informado"; HYPERLINK("https://wa.me/55" & F2; "Chamar no WhatsApp")))' == row2[6]
    assert row2[7] == "Feminino"
    assert row2[8] is None or row2[8] == ""  # Coluna I vazia (sem família)
    assert row2[9] == "Sim"
    assert row2[10] is None or row2[10] == ""  # Coluna K vazia (sem bíblia doada)
    assert row2[11] == "7 de setembro"
    assert row2[12] == "Teste 16 colunas"
    assert row2[13] == "[-12.301113,-38.6409991]"  # GeoLocalizador
    # Map formula on column O referencing N2
    assert '=IF(ISBLANK(N2); ""; IF(N2 = "[NULL,NULL]"; "Localização não capturada";IF(N2 = "[0.1,0.1]"; "Localização não capturada"; IF(N2 = "[1,1]"; "Localização não capturada"; IF(N2 = "[1,2]"; "Localização não capturada";HYPERLINK("https://www.google.com/maps?q=" & REGEXEXTRACT(N2; "-?\\d+\\.\\d+,-?\\d+\\.\\d+"); "Ver no mapa"))))))' == row2[14]
    assert row2[15] == "Missionário Jaqueline"


def test_dashboard_ui_clean_start_row_removed(client, valid_auth_headers):
    """
    Verify that the confusing inputStartRow field and instructions have been removed
    from the dashboard HTML, providing a clean export experience.
    """
    res = client.get("/dashboard", headers=valid_auth_headers)
    assert res.status_code == 200
    html = res.text
    # Confusing field and row 510 instruction removed
    assert "inputStartRow" not in html
    assert "PRÓXIMA LINHA VAZIA NA PLANILHA:" not in html
    assert "helpStepRow" not in html
    # Clean export panel exists
    assert "Exportação e Integração com Planilhas" in html
    assert "16 COLUNAS PADRONIZADAS (A..P)" in html
    assert "btnPanelExportXlsx" in html
    assert "btnPanelExportCsv" in html


