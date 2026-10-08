# Troubleshooting

## Port 8000 is already in use

Stop the existing FinSift process with `Ctrl+C`, or choose another port:

```bash
PORT=8080 ./run.sh
```

## Port 8001 is already in use

Choose another Strands port:

```bash
STRANDS_DECIDER_PORT=8099 ./run-strands.sh
```

Set `STRANDS_DECIDER_URL=http://127.0.0.1:8099` in `.env` and restart FinSift.

## Port 8002 is already in use

Choose another Laya port:

```bash
LAYA_PORT=8098 ./run-laya.sh
```

Set `LAYA_URL=http://127.0.0.1:8098` in `.env` and restart FinSift.

## A local model card says `Model unavailable`

Install and start the corresponding service:

```bash
./setup-strands.sh
./run-strands.sh
```

```bash
./setup-laya.sh
./run-laya.sh
```

Check the health endpoints:

```text
http://127.0.0.1:8001/health
http://127.0.0.1:8002/health
```

## Model setup cannot find Python

Provide the Python executable explicitly:

```bash
STRANDS_PYTHON=/opt/homebrew/bin/python3.12 ./setup-strands.sh
LAYA_PYTHON=/opt/homebrew/bin/python3.12 ./setup-laya.sh
```

## Strands is slow on first startup

The first launch downloads and initializes several gigabytes of model weights.
The first inference for a new input length may also be slower than later
requests. Keep the service running between comparisons.

## The page says `Jev mock`

Add an active `OPENROUTER_API_KEY` to `.env` and restart FinSift. Mock mode is
expected when the key is absent.

## OpenRouter reports an authentication or credit error

Confirm the key is active and the account can access `typesafe/jev-1.13`.

## No matching articles are found

Use the company's formal name and ticker, try later, or enable **Use fictional
news**. Google News coverage varies by company and time.

## Google News cannot be reached

Check the machine's internet access and VPN, proxy, or firewall settings. The
fictional-news workflow remains available.
