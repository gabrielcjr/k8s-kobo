import os
from fastapi.templating import Jinja2Templates

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
FORMS_DIR = os.path.join(BASE_DIR, "forms")
XML_FORM_PATH = os.path.join(FORMS_DIR, "Missionarios_Renovame.xml")
ASSET_JSON_PATH = os.path.join(FORMS_DIR, "Missionarios_Renovame_asset.json")

templates = Jinja2Templates(directory=TEMPLATES_DIR)
