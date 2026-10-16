# 📘 Manual do Mantenedor (Maintainer Guide)
## KoBoToolbox Native Server — Igreja Renova-me

Este documento contém todas as instruções técnicas, arquiteturais e operacionais necessárias para administrar, evoluir, diagnosticar e recuperar o servidor **KoBoToolbox / OpenRosa** da Igreja Renova-me hospedado no cluster **K3s**.

---

## 1. Contexto e Motivação do Projeto

Originalmente, a coleta de dados de missões utilizava a plataforma gratuita na nuvem da KoBoToolbox (`ee.kobotoolbox.org/x/PY2hbkKi`). Devido ao cancelamento do plano gratuito, este servidor nativo foi desenvolvido para:
1. **Eliminar dependência de planos de terceiros**, mantendo os dados proprietários dentro da infraestrutura da organização.
2. **Substituir o stack pesado original** (Postgres + Redis + Celery + Django KPI + Kobocat + Enketo), que consumiria mais de 4 GB de memória RAM, por um servidor ultraleve em Python / FastAPI / SQLite consumindo apenas ~40 MB de memória RAM.
3. **Preservar a experiência dos missionários**: não exigir reaprendizado nem alteração de fluxos. O app Android **KoBoCollect** e a coleta web offline continuam funcionando identicamente.
4. **Segurança dos dados e integração com Google Sheets**: remoção da API pública aberta desprotegida; os dados agora são transferidos com total segurança via Copiar e Colar (TSV) diretamente pelo Dashboard autenticado, gerando as fórmulas exatas de WhatsApp e Mapa.

---

## 2. Topologia de Infraestrutura

* **Servidor / VM:** Máquina host Linux ARM64 (Oracle Cloud Ampere A1) no IP público `144.22.149.93`.
* **Domínio Oficial:** `https://kobo.gabrielcjr.website` (alias histórico: `https://kobo.gabriel.website`).
* **Gateway Host (Nginx):** Executa diretamente no sistema operacional da VM, encerrando SSL/TLS via certificados Let's Encrypt gerados via Certbot:
  * Certificado: `/etc/letsencrypt/live/kobo.gabrielcjr.website/fullchain.pem`
  * Chave Privada: `/etc/letsencrypt/live/kobo.gabrielcjr.website/privkey.pem`
  * Redireciona o tráfego HTTP/HTTPS para a porta NodePort do Kubernetes: `http://127.0.0.1:30090`.
* **Cluster Kubernetes (K3s):**
  * **Namespace:** `kobo`
  * **Deployment:** `kobo-server` (1 réplica)
  * **Service:** `kobo-server` (Tipo: `NodePort`, porta `8000:30090`)
  * **Storage:** `kobo-data-pvc` (StorageClass `local-path`, 2Gi), montado em `/data`.

---

## 3. Estrutura de Código Modular e Responsabilidades

A aplicação adota o padrão **Clean Architecture / Modular FastAPI**, dividindo responsabilidades por domínio:

```
app/
├── main.py              # Ponto de entrada FastAPI, montagem de estáticos e registro de roteadores (~35 linhas)
├── config.py            # Constantes de diretórios (BASE, STATIC, TEMPLATES, FORMS) e Jinja2Templates
├── auth.py              # Helpers de autenticação HTTP Basic e proteção de endpoints
├── models.py            # Modelos Pydantic (WebSubmissionPayload, ActionSettingPayload, etc.)
├── validation.py        # Validação de regras de negócio espelhadas do XForm
├── utils.py             # Sanitização de nomes de arquivos e resolução de URL base efetiva
├── database.py          # Camada de persistência SQLite com pool thread-safe
├── openrosa.py          # Geração e parsing XML do protocolo OpenRosa (ODK / KoBoCollect)
├── formatters/          # Formatadores de saída analítica
│   ├── excel.py         # Gerador binário XLSX com fórmulas em células F{row}/N{row} e estilização
│   ├── csv_tsv.py       # Geradores CSV (KoBo e 16 colunas A..P) e TSV para clipboard
│   └── json_geojson.py  # Gerador GeoJSON RFC 7946 e KoBo API JSON
└── routers/             # Controladores FastAPI organizados por domínio
    ├── core.py          # /healthz, PWA Service Worker (/sw.js) e mídia estática
    ├── openrosa.py      # /formList, /formXml, /xformsManifest, /submission (ODK Collect)
    ├── webform.py       # Interface Web (/ e /x/{id}) e ingestão com validação (/api/submit)
    ├── dashboard.py     # Painel (/dashboard e /admin), live polling e CRUD de fichas
    ├── exports.py       # Exportações analíticas (/api/export/xlsx, /campo-missionarios.csv, TSV, GeoJSON)
    └── kobo_api.py      # Compatibilidade com a API v1 e v2 do KoBoToolbox
```

### [`app/database.py`](file:///home/ubuntu/k8s_kobo/app/database.py)
Camada de acesso a dados SQLite:
* Gerencia o arquivo `/data/kobo.db`.
* Criação de tabelas, índices e migrações transparentes.
* Normalização de coordenadas geográficas (`parse_geopoint` separa latitude, longitude, altitude e precisão).
* Cálculo das agregações de estatísticas de decisões, gêneros e missionários mais ativos.

### [`app/openrosa.py`](file:///home/ubuntu/k8s_kobo/app/openrosa.py)
Parser de submissões móveis:
* Processa requisições multipart com arquivos XML enviados pelo KoBoCollect/ODK.
* Extrai metadados do aparelho (`deviceid`), data, campos de texto, seleções e coordenadas geográficas.

### [`app/templates/webform.html`](file:///home/ubuntu/k8s_kobo/app/templates/webform.html)
Frontend do formulário missionário:
* PWA instalável com suporte a rascunhos locais e fila offline.
* **Regra de Segurança da Informação:**
  * Sem links ou botões para o dashboard.
  * Sem botão de exportação de backup local.
  * Purga imediata: Registros enviados com sucesso ao servidor são removidos imediatamente do `localStorage`, garantindo que um usuário comum não possa visualizar dados de outras pessoas ou de coletas anteriores.

### [`app/templates/dashboard.html`](file:///home/ubuntu/k8s_kobo/app/templates/dashboard.html)
Frontend do painel analítico da liderança:
* Gráficos e indicadores de KPIs (Total, Hoje, Decisões, Missionários).
* Mapa Leaflet interativo com marcadores automáticos.
* **Mecanismo de Polling em Tempo Real:** A cada 3 segundos requisita `/api/dashboard/live`, inserindo novos registros no topo da tabela com destaque verde animado e atualizando contadores sem necessidade de recarregar a página.
* **Edição e Exclusão no Painel:** A tabela possui botões de ação (Editar e Excluir). A edição abre um modal com formulário completo que atualiza o registro em tempo real no banco, tabela e mapa, enquanto a exclusão remove permanentemente a ficha com confirmação de segurança.

---

## 4. Dicionário de Dados (`submissions`)

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | INTEGER PRIMARY KEY | Identificador sequencial |
| `uuid` | TEXT UNIQUE | Identificador único universal da ficha |
| `data_date` | TEXT | Data da coleta no formato `YYYY-MM-DD` |
| `nome` | TEXT | Nome completo do entrevistado |
| `idade` | INTEGER | Idade informada |
| `telefone` | TEXT | Telefone celular (11 dígitos, DDD + número) |
| `genero` | TEXT | `Masculino` ou `Feminino` |
| `recebeu_jesus` | TEXT | Decisão espiritual (`Sim`, `Não`, `evangelico`, `decidir_depois`) |
| `endereco` | TEXT | Endereço residencial ou ponto de referência |
| `geopoint` | TEXT | String de 4 elementos: `lat long alt accuracy` |
| `latitude` | REAL | Latitude em graus decimais (ex: `-12.2570`) |
| `longitude` | REAL | Longitude em graus decimais (ex: `-38.9640`) |
| `altitude` | REAL | Altitude em metros |
| `accuracy` | REAL | Precisão do GPS em metros |
| `observacoes` | TEXT | Notas adicionais e pedidos de oração |
| `missionario` | TEXT | Nome do missionário que preencheu a ficha |
| `device_id` | TEXT | Identificador do dispositivo móvel ou `web-browser` |
| `source` | TEXT | Origem do registro: `kobo_collect` ou `web` |
| `created_at` | TEXT | Timestamp ISO-8601 da gravação no banco |

---

## 5. Procedimentos Operacionais Padrão (SOP)

### SOP-01: Executar Testes Automatizados Localmente
Sempre que fizer alterações no código, valide com a suíte de 42 testes:
```bash
# Navegar até o diretório do projeto
cd /home/ubuntu/k8s_kobo

# Executar os testes via ambiente virtual existente
/home/ubuntu/k8s_kobo/.venv/bin/pytest /home/ubuntu/k8s_kobo/tests -v
```
Todos os testes devem passar (código de saída 0).

---

### SOP-02: Construir e Atualizar o Serviço no Kubernetes (Deploy)
O cluster K3s consome a imagem localmente através do containerd:
```bash
cd /home/ubuntu/k8s_kobo

# 1. Construir a imagem Docker
docker build -t kobo-server:latest .

# 2. Importar o tar da imagem para o containerd do K3s
docker save kobo-server:latest | sudo k3s ctr images import -

# 3. Reiniciar o deployment para assumir a nova imagem
kubectl rollout restart -n kobo deploy/kobo-server

# 4. Aguardar a conclusão do rollout
kubectl rollout status -n kobo deploy/kobo-server
```

---

### SOP-03: Realizar Backup do Banco de Dados
O banco SQLite reside no volume persistente do pod. Para extrair um backup:
```bash
# Descobrir o nome do pod ativo
POD=$(kubectl get pod -n kobo -l app=kobo-server -o jsonpath="{.items[0].metadata.name}")

# Copiar o arquivo SQLite para o host
BACKUP_FILE="/home/ubuntu/kobo_backup_$(date +%Y%m%d_%H%M%S).db"
kubectl cp "kobo/${POD}:/data/kobo.db" "$BACKUP_FILE"

echo "Backup concluído em: $BACKUP_FILE"
```

---

### SOP-04: Restaurar um Backup do Banco de Dados
Caso seja necessário restaurar uma cópia de segurança:
```bash
POD=$(kubectl get pod -n kobo -l app=kobo-server -o jsonpath="{.items[0].metadata.name}")
BACKUP_FILE="/caminho/para/seu/backup.db"

# 1. Copiar o backup para o pod
kubectl cp "$BACKUP_FILE" "kobo/${POD}:/data/kobo.db"

# 2. Reiniciar o pod para recarregar as conexões
kubectl delete pod -n kobo "$POD"
```

---

### SOP-05: Como Trocar Senhas ou Credenciais
As credenciais estão definidas como variáveis de ambiente no manifesto do deployment ([`k8s/02-deployment.yaml`](file:///home/ubuntu/k8s_kobo/k8s/02-deployment.yaml)):
```yaml
env:
- name: KOBO_USER
  value: "renovamechurch"
- name: KOBO_PASS
  value: "NOVA_SENHA_AQUI"
```
Após editar o arquivo:
```bash
kubectl apply -f /home/ubuntu/k8s_kobo/k8s/02-deployment.yaml
```
*Lembre-se de atualizar também os celulares dos missionários no KoBoCollect e informar à liderança para o dashboard.*

---

### SOP-06: Renovação do Certificado SSL Let's Encrypt
O Certbot está configurado com webroot no host:
```bash
# Testar renovação em modo simulação
sudo certbot renew --dry-run

# Forçar renovação manual caso necessário
sudo certbot certonly --webroot -w /var/www/certbot -d kobo.gabrielcjr.website

# Recarregar o Nginx do host após renovação
sudo nginx -t && sudo systemctl reload nginx
```

---

### SOP-07: Resolução de Incidentes e Diagnóstico (Troubleshooting)

#### 1. Pod não sobe (`CrashLoopBackOff` ou `Error`)
```bash
# Ver eventos do pod
kubectl describe pod -n kobo -l app=kobo-server

# Ver logs da aplicação
kubectl logs -n kobo -l app=kobo-server --tail=100
```

#### 2. Site inacessível externamente (Erro 502 Bad Gateway no navegador)
1. Verifique se o pod está saudável:
   ```bash
   kubectl get pods -n kobo
   ```
2. Teste o endpoint localmente na porta NodePort do host:
   ```bash
   curl -I http://127.0.0.1:30090/healthz
   ```
3. Verifique o Nginx do host:
   ```bash
   sudo systemctl status nginx
   sudo nginx -t
   ```

#### 3. Como transferir registros para o Google Planilhas
* Por **segurança dos dados dos contatos**, o acesso anônimo sem autenticação via `=IMPORTDATA` foi bloqueado com HTTP 401.
* O fluxo oficial é realizado diretamente via Painel Administrativo (`/dashboard`):
  1. No painel de exportação ou na tabela, clique em **📋 Copiar Registros Filtrados** ou no botão individual **📋 Copiar** da linha desejada (ou utilize **📊 Baixar Excel (.xlsx)** / **📄 Baixar CSV (.csv)**).
  2. No Google Planilhas, selecione a primeira coluna e pressione `Ctrl + V`.
  3. As 16 colunas oficiais A..P serão coladas diretamente com as fórmulas de WhatsApp e Google Maps prontas e ativas (sem incluir campos de Família ou Bíblia doada, mantendo o alinhamento de colunas).

---

## 6. Histórico de Versões e Decisões Técnicas

| Data | Decisão Técnica / Mudança | Motivo |
|---|---|---|
| **Outubro/2026** | Criação do servidor nativo K3s compatível com OpenRosa | Substituição da infraestrutura paga/descontinuada do KoBoToolbox. |
| **Outubro/2026** | Omissão dos campos cidade e povoado no formulário de campo | Cidade e povoado agora são geridos de forma agregada posteriormente pela liderança. |
| **Outubro/2026** | Remoção de links do dashboard e backup local do formulário | Segurança da informação: missionários comuns não devem ver métricas gerais nem baixar bases locais. |
| **Outubro/2026** | Purga automática de formulários enviados da memória local | Impedir que terceiros tenham acesso a dados sensíveis de cadastros anteriores no aparelho do missionário. |
| **Outubro/2026** | Implementação de Live Polling (3s) no Dashboard | Permitir acompanhamento ao vivo de campanhas evangelísticas em telões e computadores da igreja sem necessidade de recarregar a página. |
| **Outubro/2026** | Remoção da API aberta e fluxo seguro de Copiar & Colar para o Google Sheets | Segurança dos dados: fechar acesso público e desprotegido a contatos; geração automática de fórmulas exatas de WhatsApp e Mapa. |
| **Outubro/2026** | Exportações dinâmicas filtradas (.xlsx e .csv) sincronizadas com o Dashboard | Permitir que a liderança baixe planilhas e arquivos CSV contendo estritamente as fichas da cidade e filtros selecionados na interface. |
| **Outubro/2026** | Padronização de 16 colunas A..P e simplificação da UI (remoção de "próxima linha vazia") | Eliminar necessidade de calcular números arbitrários de linhas; adotar numeração natural e layout oficial de 16 colunas A..P em todos os formatos (.xlsx, .csv, TSV). |

