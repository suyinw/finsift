# FinSift — Company News Scorecard

FinSift is a local equity-research prototype that turns recent company
headlines into a transparent financial-potential scorecard.

It retrieves up to ten headlines from the previous seven days, asks Jev,
Strands Decider, and Laya the same typed questions, then applies one inspectable
Python scoring policy so their judgments can be compared side by side.

FinSift is a research aid, not investment advice. Its headline-derived score
does not include financial statements, valuation, price history, analyst
estimates, or full article text.

## Video demo

[Watch the FinSift demo](docs/assets/finsift-demo.mp4) — 2 minutes 27 seconds

## Quick start with mocked Jev

FinSift requires Python 3.9 or newer. With no OpenRouter API key configured,
FinSift uses its built-in Jev mock and does not make a real call to Jev.

```bash
chmod +x run.sh
./run.sh
```

Open `http://localhost:8000`. The status bar should display **Jev mock**.

The model mode and news source are independent:

- Leave **Use fictional news** off to evaluate live Google News headlines with
  mocked Jev output.
- Enable **Use fictional news** to evaluate the bundled fictional headlines
  with mocked Jev output.

## Quick start with live Jev

Copy the environment template:

```bash
cp .env.example .env
```

Add an active OpenRouter API key to `.env`:

```dotenv
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

Start FinSift:

```bash
./run.sh
```

Open `http://localhost:8000`. The status bar should display **Jev live**.
Selecting **Jev only**, **Compare Jev + Strands**, or **Compare all three** now
sends a real request to the pinned `typesafe/jev-1.13` model through
OpenRouter.

As in mock mode, **Use fictional news** controls only the supplied headlines;
it does not change whether the Jev call is live.

## Configuration and API

The same `.env` file can configure the web port and local model service URLs:

```dotenv
PORT=8000
STRANDS_DECIDER_URL=http://127.0.0.1:8001
LAYA_URL=http://127.0.0.1:8002
```

For all environment variables and direct API usage, see
[API and configuration](docs/api.md).

## Compare all three models

Install the two local model services once:

```bash
./setup-strands.sh
./setup-laya.sh
```

Then start each service in a separate terminal:

```bash
# Terminal 1
./run-strands.sh

# Terminal 2
./run-laya.sh

# Terminal 3
./run.sh
```

Open FinSift and select **Compare all three**.

The first Strands launch downloads several gigabytes of model weights. For
Python requirements, model overrides, and health checks, see
[Model setup](docs/model-setup.md).

## Model options

| Selection | Behavior |
| --- | --- |
| **Compare all three** | Runs Jev, Strands Decider, and Laya against the same evidence |
| **Compare Jev + Strands** | Runs the original two-model comparison |
| **Jev only** | Uses live Jev when configured, otherwise the built-in mock |
| **Strands Decider only** | Calls the local service on port 8001 |
| **Laya only** | Calls the local service on port 8002 |

If a local model is unavailable, its card shows setup guidance while other
results remain usable.

## Recommended demo

1. Start Strands Decider, Laya, and FinSift.
2. Open `http://localhost:8000`.
3. Enable **Use fictional news**.
4. Choose **Compare all three**.
5. Select **Analyze last 7 days**.
6. Compare scores, categorical judgments, risk, and latency.
7. Disable fictional news and repeat with a real company.

All selected models receive the same:

- company and ticker
- headline, publisher, and publication-date records
- five typed questions
- deterministic scorecard policy

## How the score works

Each model evaluates five factors:

- business momentum: improving, stable, or deteriorating
- financial signal: positive, mixed, negative, or insufficient
- execution quality: score from 0–4
- probability of material company risk
- probability that coverage is too thin or noisy

`apply_scorecard_policy()` begins at 50, applies the same visible weights to
each model's answers, clamps the result to 0–100, and assigns one posture:

- **Candidate for deeper research**
- **Watch and investigate**
- **Low-priority candidate**
- **Insufficient coverage**

Using one policy makes score differences traceable to model output instead of
different business rules.

## Run tests

```bash
python3 -m unittest discover -s tests -v
```

The tests do not download model weights. They cover question types, state
construction, scoring bounds, insufficient coverage, input validation, model
selection, and local-model HTTP contracts.

## Data limitations

Google News RSS provides headline, publisher, date, and link metadata. FinSift
does not scrape publisher pages. Results may be tangential, duplicated,
promotional, delayed, biased, or inaccurate.

The score excludes:

- regulatory filings and financial statements
- valuation multiples and price history
- analyst estimates and earnings-call transcripts
- full article text
- portfolio objectives, risk tolerance, and position sizing

Review displayed headlines and corroborate material claims with primary
filings and company disclosures. Production or commercial use requires a news
provider with suitable redistribution and retention terms.

## Documentation

- [Model setup](docs/model-setup.md)
- [API and configuration](docs/api.md)
- [Troubleshooting](docs/troubleshooting.md)

## Project structure

```text
.
├── server.py          # News ingestion, model adapters, and score policy
├── run.sh             # Runs FinSift on port 8000
├── setup-strands.sh   # Creates the Strands virtual environment
├── run-strands.sh     # Runs Strands Decider on port 8001
├── setup-laya.sh      # Creates the Laya virtual environment
├── run-laya.sh        # Runs Laya on port 8002
├── static/            # Browser interface
├── tests/             # Unit and adapter tests
└── docs/              # Setup, API, and troubleshooting guides
```

## Upstream projects

- Strands Decider: `https://github.com/strands-labs/strands-decider`
- Strands checkpoint:
  `https://huggingface.co/StrandsAgents/strands-decider-2B-hobson-v19`
- Laya: `https://github.com/NandhaKishorM/laya#installation`

## License

FinSift is available under the [MIT License](LICENSE).
