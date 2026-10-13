import hashlib
import os
import xml.etree.ElementTree as ET
from typing import Dict, Any, Tuple, Optional

FORM_ID = "a7FqboN3tiXKPo6hSc8MzJ"
FORM_NAME = "Missionários Renova-me"
FORM_VERSION = "32 (2025-09-12 17:50:03)"
FORM_UUID = "fe67ba249d41444a9de6eea1f809669d"
FORM_MD5 = "884b8ea8aa9fd1bc7419b2a47fbb9816"

AUTH_USER = os.environ.get("KOBO_USER", "renovamechurch")
AUTH_PASS = os.environ.get("KOBO_PASS", "Rvehonraegloria")

def check_credentials(auth_header: Optional[str]) -> bool:
    if not auth_header:
        return False
    import base64
    if not auth_header.startswith("Basic "):
        return False
    try:
        encoded = auth_header[6:].strip()
        decoded = base64.b64decode(encoded).decode("utf-8")
        user, pwd = decoded.split(":", 1)
        return user == AUTH_USER and pwd == AUTH_PASS
    except Exception:
        return False

def generate_form_list_xml(base_url: str) -> str:
    # Ensure no double slashes
    base_url = base_url.rstrip("/")
    xml_content = f"""<?xml version='1.0' encoding='UTF-8' ?>
<xforms xmlns="http://openrosa.org/xforms/xformsList">
  <xform>
    <formID>{FORM_ID}</formID>
    <name>{FORM_NAME}</name>
    <majorMinorVersion>{FORM_VERSION}</majorMinorVersion>
    <version>{FORM_VERSION}</version>
    <hash>md5:{FORM_MD5}</hash>
    <descriptionText>{FORM_NAME}</descriptionText>
    <downloadUrl>{base_url}/formXml?formId={FORM_ID}</downloadUrl>
    <manifestUrl>{base_url}/xformsManifest?formId={FORM_ID}</manifestUrl>
  </xform>
</xforms>"""
    return xml_content

def generate_manifest_xml(base_url: str) -> str:
    base_url = base_url.rstrip("/")
    banner_url = f"{base_url}/media/Banner_renovam_vermelho.png"
    info_url = f"{base_url}/media/Info_app_Kobotoolbox.jpg"

    xml_content = f"""<?xml version='1.0' encoding='UTF-8' ?>
<manifest xmlns="http://openrosa.org/xforms/xformsManifest">
  <mediaFile>
    <filename>Banner_renovam_vermelho.png</filename>
    <hash>md5:6b090679758f5e2c072fc028d95a6e0c</hash>
    <downloadUrl>{banner_url}</downloadUrl>
  </mediaFile>
  <mediaFile>
    <filename>Info app Kobotoolbox.jpg</filename>
    <hash>md5:d8d196776e611b41a08c8a1bab371cba</hash>
    <downloadUrl>{info_url}</downloadUrl>
  </mediaFile>
</manifest>"""
    return xml_content

def generate_submission_success_xml() -> str:
    return """<?xml version='1.0' encoding='UTF-8' ?>
<OpenRosaResponse xmlns="http://openrosa.org/javarosa">
  <message nature="submit_success">Successful submission.</message>
</OpenRosaResponse>"""

def parse_submission_xml(xml_text: str) -> Dict[str, Any]:
    # Strip any XML declarations or whitespace
    root = ET.fromstring(xml_text)
    
    # Extract tag without namespace
    def clean_tag(elem):
        return elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

    data: Dict[str, Any] = {
        "form_id": root.attrib.get("id", FORM_ID),
        "version": root.attrib.get("version", FORM_VERSION),
        "data_date": None,
        "nome": None,
        "idade": None,
        "telefone": None,
        "genero": None,
        "recebeu_jesus": None,
        "endereco": None,
        "geopoint": None,
        "observacoes": None,
        "missionario": None,
        "device_id": None,
        "uuid": None
    }

    # Recursive search for tags
    for elem in root.iter():
        tag = clean_tag(elem)
        text = elem.text.strip() if elem.text else None
        if not text:
            continue

        if tag == "Data":
            data["data_date"] = text
        elif tag == "Nome":
            data["nome"] = text
        elif tag == "Idade":
            try:
                data["idade"] = int(text)
            except ValueError:
                data["idade"] = None
        elif tag == "Telefone":
            data["telefone"] = text
        elif tag == "Genero":
            data["genero"] = text
        elif tag == "Recebeu_a_Jesus":
            data["recebeu_jesus"] = text
        elif tag == "Endereco_ou_referencia":
            data["endereco"] = text
        elif tag == "Geolocalizador":
            data["geopoint"] = text
        elif tag == "Observacoes":
            data["observacoes"] = text
        elif tag in ("Nome_do_Mission_rio_a", "Nome_do_Missionario_a"):
            data["missionario"] = text
        elif tag == "deviceid":
            data["device_id"] = text
        elif tag == "instanceID":
            # format could be "uuid:1234..."
            data["uuid"] = text.replace("uuid:", "").strip()

    if not data["uuid"]:
        import uuid
        data["uuid"] = str(uuid.uuid4())

    return data
