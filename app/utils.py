import re
import unicodedata
from fastapi import Request

def sanitize_filename_part(text: str) -> str:
    clean = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    clean = re.sub(r"[^\w\-]", "_", clean).strip("_")
    return clean or "export"

def get_effective_base_url(request: Request) -> str:
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
    return f"{proto}://{host}"
