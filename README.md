# KoBoToolbox Native Server (ARM64 & K3s)

Servidor nativo KoBoToolbox/OpenRosa desenvolvido para execução eficiente no K3s (compatível com arquiteturas ARM64 / Ampere A1 e x86_64).

## Funcionalidades

- **Protocolo OpenRosa (ODK / KoBoCollect):**
  - Descoberta de formulários (`/formList`, `/{username}/formList`)
  - Download de definição XForm XML (`/formXml`, `/forms/{id}/form.xml`)
  - Manifesto de mídias anexas (`/xformsManifest`, `/forms/{id}/manifest.xml`)
  - Envio de submissões móveis multipart (`HEAD` & `POST /submission`, `/{username}/submission`)
- **Compatibilidade com Google Sheets & PowerBI:**
  - Baixa de dados via `=IMPORTDATA("https://kobo.gabrielcjr.website/data.csv")`
  - Endpoints de compatibilidade KoBo API v2: `/api/v2/assets/{id}/data.csv`, `export-settings/{id}/data.csv`
  - Suporte a cabeçalhos humanos em Português (`?labels=true`) e campos técnicos
  - CORS aberto (`Access-Control-Allow-Origin: *`) e suporte a requisições `GET` e `HEAD`
  - Exportação nativa Excel (`/api/export/xlsx`) e GeoJSON para mapas GIS (`/api/export/geojson`)
- **Webform Offline PWA (estilo Enketo):**
  - Rota Enketo idêntica: `/x/PY2hbkKi`
  - Cache offline via Service Worker (`/sw.js`, `/x/offline-app-worker.js`)
  - PWA instalável via Manifest (`/manifest.json`)
  - Fila de rascunhos, exportação de backup e sincronização automática quando a rede retornar
  - API de submissão web JSON: `/api/submit`
- **Painel Administrativo:**
  - Métricas em tempo real, resumo de decisões e listagem: `/dashboard` ou `/admin`
  - Autenticação HTTP Basic (`renovamechurch:Rvehonraegloria`)
  - Probe de saúde: `/healthz`

---

## Execução dos Testes Automatizados

O projeto possui uma suíte completa de testes com 36 casos de teste garantindo retrocompatibilidade total com o ecossistema KoBoToolbox.

```bash
# Ativar o ambiente virtual
source .venv/bin/activate

# Instalar dependências de desenvolvimento
pip install -r requirements-dev.txt

# Executar a suíte de testes
pytest tests -v
```

### Módulos de Teste
- `tests/test_openrosa_protocol.py`: Testa autenticação, discovery XML, download de form e submissões via KoBoCollect.
- `tests/test_kobo_api_google_sheets.py`: Testa exportações CSV/JSON/XLSX, schemas de cabeçalhos, unauthenticated access para `=IMPORTDATA` e CORS.
- `tests/test_webform_offline_pwa.py`: Testa renderização HTML, slug `/x/PY2hbkKi`, Service Worker, Manifest e submissões `/api/submit`.
- `tests/test_database_persistence.py`: Testa operações SQLite, parser de coordenadas GPS (4 componentes) e estatísticas.
- `tests/test_dashboard_auth.py`: Testa proteção Basic Auth no `/dashboard`, `/admin` e o healthcheck `/healthz`.
