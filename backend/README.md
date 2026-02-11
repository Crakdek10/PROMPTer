# PROMPTer Backend (FastAPI)

Backend para **PROMPTer**: WebSocket STT (transcripción) + HTTP LLM (generación),
con arquitectura **enchufable de providers**.

---

## Requisitos

- Python **3.13+** (recomendado)
- Windows / macOS / Linux

---

## Instalación

Desde la carpeta `backend`:

### 1. Crear entorno virtual

**Windows**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**macOS / Linux**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

---

## Ejecutar el servidor

```bash
uvicorn app.main:app --reload
```

Servidor por defecto:
http://127.0.0.1:8000

Documentación automática:
- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json

---

## Endpoints

### Health

**GET** `/health`

Respuesta esperada:
```json
{ "status": "ok" }
```

---

### Providers

**GET** `/providers/stt`
**GET** `/providers/llm`

Ejemplo de respuesta:
```json
{
  "items": [
    {
      "name": "cloud_stub",
      "type": "stt",
      "status": "ready",
      "description": "Mock realista (partial por chunk, final cada 3)."
    }
  ]
}
```

---

### LLM

**POST** `/llm/generate`

Body mínimo:
```json
{
  "messages": [
    { "role": "user", "content": "Hola" }
  ],
  "provider": "openai_compat",
  "config": {}
}
```

> Nota:
> Si no se configuran `base_url`, `api_key` y `model`, el backend
> responderá con un **error de configuración (HTTP 400)**.

Ejemplo con configuración completa:
```json
{
  "messages": [
    { "role": "user", "content": "Dime un chiste corto" }
  ],
  "provider": "openai_compat",
  "config": {
    "base_url": "https://api.openai.com/v1",
    "api_key": "TU_API_KEY",
    "model": "gpt-4o-mini"
  }
}
```

---

### STT WebSocket

**WS** `/ws/stt`

#### Protocolo de mensajes

**Cliente → Servidor**

1. start
```json
{
  "type": "start",
  "session_id": "s1",
  "config": {
    "lang": "es",
    "provider": "cloud_stub"
  }
}
```

2. audio (PCM16 en base64)
```json
{
  "type": "audio",
  "format": "pcm16",
  "sample_rate": 16000,
  "data": "<base64>"
}
```

3. stop
```json
{
  "type": "stop"
}
```

---

**Servidor → Cliente**

ready
```json
{
  "type": "ready",
  "session_id": "s1"
}
```

partial
```json
{
  "type": "partial",
  "session_id": "s1",
  "text": "(mock) escuchando... chunk=1"
}
```

final
```json
{
  "type": "final",
  "session_id": "s1",
  "text": "(mock) transcripción final #1"
}
```

error
```json
{
  "type": "error",
  "session_id": "s1",
  "message": "..."
}
```

---

### Notas sobre audio

- **format**: actualmente solo `pcm16`
- **sample_rate**: permitido entre **8000 y 48000**
- **data**: audio PCM16 codificado en base64

---

## Tests

Desde la carpeta `backend`:

```bash
pytest
```

---

## Estructura del proyecto (resumen)

```
app/api/        -> Routers HTTP y WebSocket
app/services/   -> Lógica de negocio (routers internos, sesiones)
app/providers/  -> Providers enchufables (STT / LLM)
app/utils/      -> Validaciones y helpers
app/core/       -> Configuración, logging y errores
app/tests/      -> Tests con pytest
```