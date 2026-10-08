# Model setup

FinSift can compare Jev, Strands Decider, and Laya. Each local model runs as a
separate service so its ML dependencies and weights remain isolated from the
standard-library web application.

## Prerequisites

- macOS or Linux
- Python 3.9 or newer for FinSift
- Python 3.10 or newer for Strands Decider and Laya
- Internet access for live Google News results
- an OpenRouter API key only for live Jev
- approximately 5 GB of storage for Strands model weights

## Live Jev

Copy the environment template:

```bash
cp .env.example .env
```

Add an OpenRouter API key:

```dotenv
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

Restart FinSift. The status bar should display **Jev live**.

The adapter calls OpenRouter's Decisions API with the pinned
`typesafe/jev-1.13` model. The key stays in the local Python process and is
never sent to the browser.

Without a key, FinSift uses its built-in Jev mock.

## Strands Decider

The setup script creates `.venv-strands`, installs a tested Strands revision,
and configures its Apple Silicon MLX dependencies:

```bash
chmod +x setup-strands.sh run-strands.sh
./setup-strands.sh
```

To select a Python installation or test a deliberate revision upgrade:

```bash
STRANDS_PYTHON=/path/to/python3.12 ./setup-strands.sh
STRANDS_DECIDER_REVISION=commit-or-tag ./setup-strands.sh
```

Start the service:

```bash
./run-strands.sh
```

It serves `StrandsAgents/strands-decider-2B-hobson-v19` at
`http://127.0.0.1:8001`. The first launch downloads the checkpoint and
`Qwen/Qwen3.5-2B-Base`; later launches reuse the Hugging Face cache.

Verify the service:

```bash
curl http://127.0.0.1:8001/health
```

Configuration overrides:

```bash
STRANDS_DECIDER_DEVICE=mps ./run-strands.sh
STRANDS_DECIDER_DEVICE=cpu ./run-strands.sh
STRANDS_DECIDER_PORT=8099 ./run-strands.sh
STRANDS_DECIDER_MODEL=organization/checkpoint ./run-strands.sh
```

If the port changes, update `.env` and restart FinSift:

```dotenv
STRANDS_DECIDER_URL=http://127.0.0.1:8099
```

## Laya

The setup script creates a separate environment and installs the tested Laya
version:

```bash
chmod +x setup-laya.sh run-laya.sh
./setup-laya.sh
```

To select Python or test a deliberate version upgrade:

```bash
LAYA_PYTHON=/path/to/python3.12 ./setup-laya.sh
LAYA_VERSION=x.y.z ./setup-laya.sh
```

Start Laya:

```bash
./run-laya.sh
```

It serves the `typed-decisions` checkpoint at `http://127.0.0.1:8002`, using
MPS on Apple Silicon and CPU elsewhere.

Verify the service:

```bash
curl http://127.0.0.1:8002/health
```

Configuration overrides:

```bash
LAYA_DEVICE=cpu ./run-laya.sh
LAYA_PORT=8098 ./run-laya.sh
```

If the port changes, update `.env` and restart FinSift:

```dotenv
LAYA_URL=http://127.0.0.1:8098
```

## Run the complete stack

Keep each process running in its own terminal:

```bash
./run-strands.sh
./run-laya.sh
./run.sh
```

Open `http://localhost:8000` and choose **Compare all three**.
