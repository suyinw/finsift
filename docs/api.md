# API and configuration

## Environment variables

Copy the template before changing configuration:

```bash
cp .env.example .env
```

FinSift recognizes:

```dotenv
OPENROUTER_API_KEY=sk-or-v1-your-key-here
PORT=8000
STRANDS_DECIDER_URL=http://127.0.0.1:8001
LAYA_URL=http://127.0.0.1:8002
```

Restart FinSift after changing `.env`.

## Analyze a company

With FinSift running:

```bash
curl -X POST http://127.0.0.1:8000/api/analyze \
  -H 'Content-Type: application/json' \
  --data '{
    "company": "Northstar Cloud",
    "ticker": "NSTR",
    "model_selection": "all",
    "use_mock_news": true
  }'
```

`model_selection` accepts:

- `jev`
- `strands`
- `laya`
- `both`
- `all`

Set `use_mock_news` to `false` and provide a real company to retrieve live
headlines.

Each completed model call prints its raw JSON response in the FinSift terminal
before the application adds its derived score and posture.

## Change the web application port

Set the port in `.env`:

```dotenv
PORT=8080
```

Or override it for one run:

```bash
PORT=8080 ./run.sh
```

Open `http://localhost:8080`.

## Latency fields

The response reports:

- request parsing and validation
- news retrieval
- model-state preparation
- each model's inference and business logic
- response preparation and serialization
- browser transport, parsing, and rendering
- end-to-end time

The model pipeline total includes inference, terminal logging, business logic,
and coordination. The server total covers all server-side stages. End-to-end
time also includes transport and browser rendering.
