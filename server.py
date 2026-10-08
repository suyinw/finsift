#!/usr/bin/env python3
"""Local company-news scorecard powered by typed decision models."""

from __future__ import annotations

import json
import math
import mimetypes
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlencode, urlsplit
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
OPENROUTER_URL = "https://openrouter.ai/api/alpha/decisions"
GOOGLE_NEWS_URL = "https://news.google.com/rss/search"
JEV_MODEL = "typesafe/jev-1.13"
STRANDS_DECIDER_DEFAULT_URL = "http://127.0.0.1:8001"
LAYA_DEFAULT_URL = "http://127.0.0.1:8002"
LAYA_MODEL = "typed-decisions"
ARTICLE_LIMIT = 10


def elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)


MOCK_ARTICLES = [
    {
        "title": "Northstar Cloud reports stronger enterprise demand and raises outlook",
        "publisher": "Market Ledger",
        "published": "2026-10-02T15:30:00+00:00",
        "url": "#",
    },
    {
        "title": "Northstar launches lower-cost inference service for mid-market customers",
        "publisher": "The Technology Wire",
        "published": "2026-10-02T09:10:00+00:00",
        "url": "#",
    },
    {
        "title": "Analysts debate margin impact of Northstar's accelerated data-center spending",
        "publisher": "Capital Review",
        "published": "2026-10-01T18:00:00+00:00",
        "url": "#",
    },
    {
        "title": "Northstar signs multi-year cloud agreement with global retailer",
        "publisher": "Business Dispatch",
        "published": "2026-09-30T14:45:00+00:00",
        "url": "#",
    },
    {
        "title": "Regulator opens preliminary review of Northstar marketplace practices",
        "publisher": "Policy Journal",
        "published": "2026-09-29T21:20:00+00:00",
        "url": "#",
    },
    {
        "title": "Northstar expands renewable-energy purchases for regional data centers",
        "publisher": "Energy Daily",
        "published": "2026-09-29T12:05:00+00:00",
        "url": "#",
    },
    {
        "title": "Northstar hiring remains selective as productivity program continues",
        "publisher": "Workplace News",
        "published": "2026-09-28T16:40:00+00:00",
        "url": "#",
    },
    {
        "title": "Northstar service disruption resolved after ninety minutes",
        "publisher": "Cloud Status Weekly",
        "published": "2026-09-27T20:15:00+00:00",
        "url": "#",
    },
]


def load_dotenv() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def strands_decider_url() -> str:
    return os.environ.get(
        "STRANDS_DECIDER_URL", STRANDS_DECIDER_DEFAULT_URL
    ).rstrip("/")


def laya_url() -> str:
    return os.environ.get("LAYA_URL", LAYA_DEFAULT_URL).rstrip("/")


def jev_questions() -> dict:
    return {
        "business_momentum": {
            "type": "choice",
            "instructions": (
                "Based only on the supplied headlines, classify the direction of "
                "company operating and business momentum during this news window."
            ),
            "criteria": {
                "improving": "Coverage predominantly indicates improving demand, execution, or growth.",
                "stable": "Coverage is balanced or indicates broadly stable business conditions.",
                "deteriorating": "Coverage predominantly indicates weakening demand, execution, or growth.",
            },
        },
        "financial_signal": {
            "type": "choice",
            "instructions": (
                "Classify the overall financial signal contained explicitly in the headlines."
            ),
            "criteria": {
                "positive": "Headlines contain material positive financial or commercial signals.",
                "mixed": "Positive and negative financial signals are balanced or ambiguous.",
                "negative": "Headlines contain material negative financial or commercial signals.",
                "insufficient": "The headlines contain too little financial information to classify.",
            },
        },
        "execution_quality": {
            "type": "score",
            "instructions": (
                "Score the operational execution signal expressed by the supplied headlines."
            ),
            "criteria": [
                "Severe execution concerns",
                "More execution concerns than strengths",
                "Mixed or unclear execution",
                "More execution strengths than concerns",
                "Consistently strong execution signals",
            ],
        },
        "material_risk": {
            "type": "noul",
            "instructions": (
                "Do the headlines identify a material legal, regulatory, operational, "
                "governance, or balance-sheet risk?"
            ),
            "criteria": {
                "true": "At least one concrete, potentially material company risk is present.",
                "false": "No concrete, potentially material company risk is present.",
            },
        },
        "thin_coverage": {
            "type": "noul",
            "instructions": (
                "Is this headline set too thin, repetitive, promotional, or tangential "
                "to support a useful company-health research signal?"
            ),
            "criteria": {
                "true": "Coverage quality or relevance is too weak for a useful signal.",
                "false": "Coverage is sufficiently varied and relevant for a provisional signal.",
            },
        },
    }


def validate_company(payload: dict) -> tuple[str, str]:
    company = str(payload.get("company", "")).strip()
    ticker = str(payload.get("ticker", "")).strip().upper()
    if not 2 <= len(company) <= 100:
        raise ValueError("Company name must contain 2–100 characters.")
    if ticker and not re.fullmatch(r"[A-Z0-9.\-]{1,12}", ticker):
        raise ValueError("Ticker contains unsupported characters.")
    return company, ticker


def validate_model_selection(payload: dict) -> str:
    selection = str(payload.get("model_selection", "all")).strip().lower()
    if selection not in {"jev", "strands", "laya", "both", "all"}:
        raise ValueError(
            "Model selection must be jev, strands, laya, both, or all."
        )
    return selection


def fetch_google_news(company: str, ticker: str) -> list[dict]:
    terms = f'"{company}"'
    if ticker:
        terms += f" {ticker}"
    query = f"{terms} when:7d"
    params = {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
    request = Request(
        f"{GOOGLE_NEWS_URL}?{urlencode(params)}",
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; FinSift/1.0)",
            "Accept": "application/rss+xml, application/xml, text/xml",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            xml_body = response.read()
    except HTTPError as error:
        raise RuntimeError(f"Google News returned HTTP {error.code}.") from error
    except URLError as error:
        raise RuntimeError(f"Could not reach Google News: {error.reason}") from error

    try:
        root = ET.fromstring(xml_body)
    except ET.ParseError as error:
        raise RuntimeError("Google News returned malformed RSS.") from error

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    articles = []
    seen = set()
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        source_node = item.find("source")
        publisher = (
            (source_node.text or "").strip()
            if source_node is not None
            else "Unknown publisher"
        )
        published_text = (item.findtext("pubDate") or "").strip()
        try:
            published = parsedate_to_datetime(published_text)
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            published = published.astimezone(timezone.utc)
        except (TypeError, ValueError):
            continue
        normalized = re.sub(r"\s+", " ", title).lower()
        if not title or normalized in seen or published < cutoff:
            continue
        seen.add(normalized)
        articles.append(
            {
                "title": title,
                "publisher": publisher,
                "published": published.isoformat(),
                "url": link,
            }
        )
    articles.sort(key=lambda article: article["published"], reverse=True)
    return articles[:ARTICLE_LIMIT]


def build_state(company: str, ticker: str, articles: list[dict]) -> dict:
    return {
        "company": company,
        "ticker": ticker or "not supplied",
        "coverage_window": "previous 7 days",
        "source_scope": (
            "Google News RSS headlines and publisher metadata only; article bodies "
            "and company fundamentals are not included"
        ),
        "article_count": len(articles),
        "articles": [
            {
                "headline": article["title"],
                "publisher": article["publisher"],
                "published": article["published"],
            }
            for article in articles
        ],
    }


def log_raw_model_output(model_name: str, runtime: str, result: dict) -> None:
    """Print the model response before the scorecard policy adds derived fields."""
    label = {
        "jev": "Jev",
        "strands": "Strands Decider",
        "laya": "Laya",
    }.get(model_name, model_name)
    print(f"\n[model-output] {label} ({runtime}) raw response:")
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    print("[model-output] end raw response\n", flush=True)


def call_jev(state: dict, api_key: str) -> dict:
    body = json.dumps(
        {"model": JEV_MODEL, "state": state, "questions": jev_questions()}
    ).encode("utf-8")
    request = Request(
        OPENROUTER_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "FinSift Company News Scorecard",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        try:
            message = json.loads(detail).get("error", {}).get("message", detail)
        except json.JSONDecodeError:
            message = detail
        raise RuntimeError(f"OpenRouter returned {error.code}: {message}") from error
    except URLError as error:
        raise RuntimeError(f"Could not reach OpenRouter: {error.reason}") from error


def call_strands_decider(state: dict) -> dict:
    body = json.dumps(
        {"state": state, "questions": jev_questions()}
    ).encode("utf-8")
    request = Request(
        f"{strands_decider_url()}/v1/systemone",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
            result["provider"] = "Local Strands Decider"
            return result
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(detail)
            message = parsed.get("detail", parsed)
        except json.JSONDecodeError:
            message = detail
        raise RuntimeError(
            f"Strands Decider returned {error.code}: {message}"
        ) from error
    except URLError as error:
        raise RuntimeError(
            "Strands Decider is not reachable on port 8001. "
            "Run ./setup-strands.sh once, then start ./run-strands.sh."
        ) from error


def strands_decider_status() -> dict:
    request = Request(f"{strands_decider_url()}/health", method="GET")
    try:
        with urlopen(request, timeout=1) as response:
            result = json.loads(response.read().decode("utf-8"))
            return {
                "available": result.get("status") == "ok",
                "model": result.get("model", "strands-decider"),
                "device": result.get("device", "unknown"),
            }
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return {
            "available": False,
            "model": "StrandsAgents/strands-decider-2B-hobson-v19",
            "device": None,
        }


def call_laya(state: dict) -> dict:
    body = json.dumps(
        {
            "model": LAYA_MODEL,
            "state": state,
            "questions": jev_questions(),
        }
    ).encode("utf-8")
    request = Request(
        f"{laya_url()}/v1/systemone",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
            result["provider"] = "Local Laya"
            return result
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(detail)
            message = parsed.get("detail", parsed)
        except json.JSONDecodeError:
            message = detail
        raise RuntimeError(f"Laya returned {error.code}: {message}") from error
    except URLError as error:
        raise RuntimeError(
            "Laya is not reachable on port 8002. "
            "Run ./setup-laya.sh once, then start ./run-laya.sh."
        ) from error


def laya_status() -> dict:
    request = Request(f"{laya_url()}/health", method="GET")
    try:
        with urlopen(request, timeout=1) as response:
            result = json.loads(response.read().decode("utf-8"))
            loaded_models = result.get("loaded", [])
            return {
                "available": result.get("status") == "ok",
                "model": LAYA_MODEL,
                "loaded": LAYA_MODEL in loaded_models,
                "device": result.get("device", "unknown"),
            }
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return {
            "available": False,
            "model": LAYA_MODEL,
            "loaded": False,
            "device": None,
        }


def softmax(values: dict[str, float]) -> dict[str, float]:
    peak = max(values.values())
    exp_values = {key: math.exp(value - peak) for key, value in values.items()}
    total = sum(exp_values.values())
    return {key: value / total for key, value in exp_values.items()}


def mock_jev(articles: list[dict]) -> dict:
    text = " ".join(article["title"].lower() for article in articles)
    positive = (
        "beat",
        "growth",
        "raises",
        "stronger",
        "expands",
        "launch",
        "wins",
        "agreement",
        "improves",
        "record",
    )
    negative = (
        "miss",
        "cuts",
        "weak",
        "lawsuit",
        "probe",
        "review",
        "outage",
        "disruption",
        "debt",
        "decline",
        "layoff",
        "investigation",
    )
    positive_hits = sum(text.count(word) for word in positive)
    negative_hits = sum(text.count(word) for word in negative)
    balance = positive_hits - negative_hits
    momentum_probs = softmax(
        {"improving": balance, "stable": 1.2, "deteriorating": -balance}
    )
    financial_probs = softmax(
        {
            "positive": balance * 0.8,
            "mixed": 1.1,
            "negative": -balance * 0.8,
            "insufficient": 2.0 if len(articles) < 4 else -0.5,
        }
    )
    execution = min(4.0, max(0.0, 2 + balance * 0.34))
    material_risk = min(0.95, 0.08 + negative_hits * 0.12)
    publisher_count = len({article["publisher"] for article in articles})
    thin_coverage = max(
        0.05,
        min(0.95, 0.72 - len(articles) * 0.06 - publisher_count * 0.025),
    )
    return {
        "id": "local-mock",
        "model": "local/mock-news-engine",
        "provider": "Local deterministic mock",
        "answers": {
            "business_momentum": {
                "type": "choice",
                "choice": max(momentum_probs, key=momentum_probs.get),
                "confidence": round(max(momentum_probs.values()), 4),
                "probabilities": {
                    key: round(value, 4) for key, value in momentum_probs.items()
                },
            },
            "financial_signal": {
                "type": "choice",
                "choice": max(financial_probs, key=financial_probs.get),
                "confidence": round(max(financial_probs.values()), 4),
                "probabilities": {
                    key: round(value, 4) for key, value in financial_probs.items()
                },
            },
            "execution_quality": {
                "type": "score",
                "score": round(execution, 3),
                "confidence": 0.62,
                "probabilities": {},
                "legend": {
                    "0": "Severe execution concerns",
                    "1": "More execution concerns than strengths",
                    "2": "Mixed or unclear execution",
                    "3": "More execution strengths than concerns",
                    "4": "Consistently strong execution signals",
                },
            },
            "material_risk": {"type": "noul", "noul": round(material_risk, 4)},
            "thin_coverage": {"type": "noul", "noul": round(thin_coverage, 4)},
        },
        "usage": {"input_tokens": 0, "output_tokens": 0, "cost": 0},
    }


def apply_scorecard_policy(raw_result: dict, article_count: int) -> dict:
    answers = raw_result["answers"]
    momentum = answers["business_momentum"]
    financial = answers["financial_signal"]
    execution = float(answers["execution_quality"]["score"])
    risk = float(answers["material_risk"]["noul"])
    thin = float(answers["thin_coverage"]["noul"])

    score = 50.0
    score += {"improving": 15, "stable": 0, "deteriorating": -15}[momentum["choice"]]
    score += {
        "positive": 18,
        "mixed": 0,
        "negative": -18,
        "insufficient": -8,
    }[financial["choice"]]
    score += (execution - 2) * 6
    score -= risk * 18
    score -= thin * 10
    score = round(max(0, min(100, score)))

    if article_count < 3 or thin >= 0.72:
        posture = "Insufficient coverage"
        posture_code = "insufficient"
    elif score >= 70 and risk < 0.55:
        posture = "Candidate for deeper research"
        posture_code = "candidate"
    elif score >= 48:
        posture = "Watch and investigate"
        posture_code = "watch"
    else:
        posture = "Low-priority candidate"
        posture_code = "low"

    raw_result["scorecard"] = {
        "score": score,
        "posture": posture,
        "posture_code": posture_code,
        "article_count": article_count,
        "components": {
            "business_momentum": momentum["choice"],
            "financial_signal": financial["choice"],
            "execution_quality": execution,
            "material_risk": risk,
            "thin_coverage": thin,
        },
    }
    return raw_result


class DemoHandler(SimpleHTTPRequestHandler):
    server_version = "FinSift/1.0"

    def translate_path(self, path: str) -> str:
        clean_path = unquote(urlsplit(path).path)
        if clean_path == "/":
            clean_path = "/index.html"
        target = (STATIC_DIR / clean_path.lstrip("/")).resolve()
        if target != STATIC_DIR and STATIC_DIR not in target.parents:
            return str(STATIC_DIR / "__not_found__")
        return str(target)

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/api/status":
            jev_mode = "live" if os.environ.get("OPENROUTER_API_KEY") else "mock"
            self.send_json(
                {
                    "jev": {
                        "available": True,
                        "mode": jev_mode,
                        "model": (
                            JEV_MODEL
                            if jev_mode == "live"
                            else "local/mock-news-engine"
                        ),
                    },
                    "strands": strands_decider_status(),
                    "laya": laya_status(),
                    "news_source": "Google News RSS",
                }
            )
            return
        if path.startswith("/api/"):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        super().do_GET()

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/api/analyze":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        request_started = time.perf_counter()
        try:
            parsing_started = time.perf_counter()
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length > 10_000:
                raise ValueError("Request is too large.")
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            company, ticker = validate_company(payload)
            model_selection = validate_model_selection(payload)
            use_mock_news = bool(payload.get("use_mock_news", False))
            request_parsing_latency = elapsed_ms(parsing_started)

            news_started = time.perf_counter()
            if use_mock_news:
                articles = [dict(article) for article in MOCK_ARTICLES]
                news_mode = "fictional"
            else:
                articles = fetch_google_news(company, ticker)
                news_mode = "live"
            news_latency = elapsed_ms(news_started)
            if not articles:
                raise RuntimeError("No matching articles were found in the previous seven days.")

            state_started = time.perf_counter()
            state = build_state(company, ticker, articles)
            if model_selection == "all":
                requested_models = ["jev", "strands", "laya"]
            elif model_selection == "both":
                requested_models = ["jev", "strands"]
            else:
                requested_models = [model_selection]
            state_preparation_latency = elapsed_ms(state_started)
            results = {}
            for model_name in requested_models:
                try:
                    model_pipeline_started = time.perf_counter()
                    if model_name == "jev":
                        api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
                        runtime = "live" if api_key else "mock"
                        inference_started = time.perf_counter()
                        raw_result = (
                            call_jev(state, api_key)
                            if api_key
                            else mock_jev(articles)
                        )
                    else:
                        runtime = "local"
                        inference_started = time.perf_counter()
                        raw_result = (
                            call_strands_decider(state)
                            if model_name == "strands"
                            else call_laya(state)
                        )
                    inference_latency_ms = elapsed_ms(inference_started)
                    logging_started = time.perf_counter()
                    log_raw_model_output(model_name, runtime, raw_result)
                    logging_latency_ms = elapsed_ms(logging_started)
                    business_logic_started = time.perf_counter()
                    model_result = apply_scorecard_policy(
                        raw_result, len(articles)
                    )
                    business_logic_latency_ms = elapsed_ms(
                        business_logic_started
                    )
                    model_result["runtime"] = runtime
                    model_result["inference_latency_ms"] = inference_latency_ms
                    model_result["logging_latency_ms"] = logging_latency_ms
                    model_result["business_logic_latency_ms"] = (
                        business_logic_latency_ms
                    )
                    model_result["model_pipeline_latency_ms"] = elapsed_ms(
                        model_pipeline_started
                    )
                    results[model_name] = model_result
                except RuntimeError as error:
                    results[model_name] = {
                        "error": str(error),
                        "runtime": "unavailable",
                        "model": (
                            JEV_MODEL
                            if model_name == "jev"
                            else (
                                "StrandsAgents/strands-decider-2B-hobson-v19"
                                if model_name == "strands"
                                else LAYA_MODEL
                            )
                        ),
                    }

            response_preparation_started = time.perf_counter()
            response_payload = {
                "company": company,
                "ticker": ticker,
                "articles": articles,
                "news_mode": news_mode,
                "model_selection": model_selection,
                "results": results,
                "timings": {
                    "request_parsing_ms": request_parsing_latency,
                    "news_retrieval_ms": news_latency,
                    "state_preparation_ms": state_preparation_latency,
                },
            }
            response_payload["timings"]["response_preparation_ms"] = elapsed_ms(
                response_preparation_started
            )
            self.send_json(response_payload, timing_started=request_started)
        except (ValueError, json.JSONDecodeError) as error:
            self.send_json({"error": str(error)}, status=HTTPStatus.BAD_REQUEST)
        except RuntimeError as error:
            self.send_json({"error": str(error)}, status=HTTPStatus.BAD_GATEWAY)
        except Exception as error:
            print(f"Unhandled error: {error}", file=sys.stderr)
            self.send_json(
                {"error": "The local server encountered an unexpected error."},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def send_json(
        self,
        payload: dict,
        status: int = HTTPStatus.OK,
        timing_started=None,
    ) -> None:
        serialization_started = time.perf_counter()
        body = json.dumps(payload).encode("utf-8")
        serialization_ms = elapsed_ms(serialization_started)
        server_processing_ms = (
            elapsed_ms(timing_started)
            if timing_started is not None
            else None
        )
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if server_processing_ms is not None:
            self.send_header(
                "X-Response-Serialization-Ms", str(serialization_ms)
            )
            self.send_header("X-Server-Processing-Ms", str(server_processing_ms))
        self.end_headers()
        self.wfile.write(body)

    def guess_type(self, path: str) -> str:
        return mimetypes.guess_type(path)[0] or "application/octet-stream"

    def log_message(self, format: str, *args: object) -> None:
        print(f"[demo] {self.address_string()} - {format % args}")


def main() -> None:
    load_dotenv()
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), DemoHandler)
    mode = "LIVE JEV" if os.environ.get("OPENROUTER_API_KEY") else "MOCK JEV"
    print(f"FinSift Company News Scorecard: http://localhost:{port}")
    print(f"Mode: {mode}; Strands Decider expected at {strands_decider_url()}")
    print(f"Laya typed-decisions expected at {laya_url()}")
    print("Live news available through Google News RSS")
    if mode == "MOCK JEV":
        print("Add OPENROUTER_API_KEY to .env and restart for live Jev decisions.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
