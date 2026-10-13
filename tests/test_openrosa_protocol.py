import xml.etree.ElementTree as ET
import pytest

def test_form_list_unauthorized_with_bad_creds(client):
    headers = {"Authorization": "Basic d3Jvbmc6Y3JlZHM="}
    res = client.get("/formList", headers=headers)
    assert res.status_code == 401
    assert 'Basic realm="KoBoToolbox"' in res.headers.get("www-authenticate", "")

def test_form_list_authorized(client, valid_auth_headers):
    res = client.get("/formList", headers=valid_auth_headers)
    assert res.status_code == 200
    assert res.headers["x-openrosa-version"] == "1.0"
    assert "text/xml" in res.headers["content-type"]
    
    root = ET.fromstring(res.text)
    assert root.tag == "{http://openrosa.org/xforms/xformsList}xforms"
    xform = root.find("{http://openrosa.org/xforms/xformsList}xform")
    assert xform is not None
    form_id = xform.find("{http://openrosa.org/xforms/xformsList}formID").text
    assert form_id == "a7FqboN3tiXKPo6hSc8MzJ"
    name = xform.find("{http://openrosa.org/xforms/xformsList}name").text
    assert name == "Missionários Renova-me"
    download_url = xform.find("{http://openrosa.org/xforms/xformsList}downloadUrl").text
    assert "/formXml" in download_url

def test_form_list_user_endpoint_backward_compat(client, valid_auth_headers):
    res = client.get("/renovamechurch/formList", headers=valid_auth_headers)
    assert res.status_code == 200
    assert "a7FqboN3tiXKPo6hSc8MzJ" in res.text

def test_form_xml_download(client):
    res = client.get("/formXml?formId=a7FqboN3tiXKPo6hSc8MzJ")
    assert res.status_code == 200
    assert res.headers["x-openrosa-version"] == "1.0"
    assert "text/xml" in res.headers["content-type"]
    assert "Missionários Renova-me" in res.text
    assert "<Data" in res.text
    assert "<Nome" in res.text
    assert "<Telefone" in res.text

def test_form_xml_path_endpoints(client):
    res1 = client.get("/forms/a7FqboN3tiXKPo6hSc8MzJ/form.xml")
    assert res1.status_code == 200
    res2 = client.get("/renovamechurch/forms/a7FqboN3tiXKPo6hSc8MzJ/form.xml")
    assert res2.status_code == 200

def test_manifest_download(client):
    res = client.get("/xformsManifest?formId=a7FqboN3tiXKPo6hSc8MzJ")
    assert res.status_code == 200
    assert res.headers["x-openrosa-version"] == "1.0"
    root = ET.fromstring(res.text)
    assert root.tag == "{http://openrosa.org/xforms/xformsManifest}manifest"
    media_files = root.findall("{http://openrosa.org/xforms/xformsManifest}mediaFile")
    assert len(media_files) >= 2
    filenames = [m.find("{http://openrosa.org/xforms/xformsManifest}filename").text for m in media_files]
    assert "Banner_renovam_vermelho.png" in filenames

def test_media_file_serving(client):
    res = client.get("/media/Banner_renovam_vermelho.png")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/png"
    assert len(res.content) > 1000

def test_submission_head(client, valid_auth_headers):
    res = client.head("/submission", headers=valid_auth_headers)
    assert res.status_code == 204
    assert res.headers["x-openrosa-version"] == "1.0"
    assert "x-openrosa-accept-content-length" in res.headers

def test_submission_post_xml(client, valid_auth_headers, sample_xml_submission):
    files = {"xml_submission_file": ("submission.xml", sample_xml_submission, "text/xml")}
    res = client.post("/submission", files=files, headers=valid_auth_headers)
    assert res.status_code == 201
    assert res.headers["x-openrosa-version"] == "1.0"
    assert "submit_success" in res.text

def test_submission_user_post_xml(client, valid_auth_headers, sample_xml_submission):
    files = {"xml_submission_file": ("submission.xml", sample_xml_submission, "text/xml")}
    res = client.post("/renovamechurch/submission", files=files, headers=valid_auth_headers)
    assert res.status_code == 201
    assert "submit_success" in res.text
