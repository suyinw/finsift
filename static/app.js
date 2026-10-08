const form = document.querySelector("#analysis-form");
const button = document.querySelector("#analyze-button");
const errorBox = document.querySelector("#error");
const dashboard = document.querySelector("#dashboard");
const emptyDashboard = document.querySelector("#empty-dashboard");

const pct = (value) => `${Math.round((Number(value) || 0) * 100)}%`;
const duration = (milliseconds) => {
  const value = Number(milliseconds) || 0;
  if (value < 1) return `${value.toFixed(2)} ms`;
  if (value < 1000) return `${Math.round(value)} ms`;
  return `${(value / 1000).toFixed(value >= 10000 ? 1 : 2)} s`;
};
const modelLabels = {
  jev: "Jev 1.13",
  strands: "Strands Decider v19",
  laya: "Laya Typed Decisions",
};

function setStatus(status) {
  const chip = document.querySelector("#status-chip");
  const strandsReady = Boolean(status.strands?.available);
  const layaReady = Boolean(status.laya?.available);
  const jevLabel = status.jev?.mode === "live" ? "Jev live" : "Jev mock";
  const strandsLabel = strandsReady ? "Strands ready" : "Strands offline";
  const layaLabel = layaReady ? "Laya ready" : "Laya offline";
  chip.classList.toggle(
    "live",
    status.jev?.mode === "live" && strandsReady && layaReady,
  );
  document.querySelector("#status-label").textContent =
    `${jevLabel} · ${strandsLabel} · ${layaLabel}`;
}

fetch("/api/status")
  .then((response) => response.json())
  .then(setStatus)
  .catch(() => {
    document.querySelector("#status-label").textContent = "Server unavailable";
  });

function addText(parent, tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  element.textContent = text;
  parent.appendChild(element);
  return element;
}

function addMeter(parent, value, risk = false, labels = []) {
  const meter = document.createElement("div");
  meter.className = risk ? "meter risk" : "meter";
  const fill = document.createElement("i");
  fill.style.width = `${Math.max(0, Math.min(100, value))}%`;
  meter.appendChild(fill);
  parent.appendChild(meter);
  if (labels.length === 2) {
    const scale = document.createElement("div");
    scale.className = "meter-scale";
    addText(scale, "span", "", labels[0]);
    addText(scale, "span", "", labels[1]);
    parent.appendChild(scale);
  }
}

const choiceTone = {
  improving: "favorable",
  positive: "favorable",
  stable: "neutral",
  mixed: "neutral",
  deteriorating: "adverse",
  negative: "adverse",
  insufficient: "unknown",
};

const choiceToneLabel = {
  favorable: "favorable",
  neutral: "neutral / mixed",
  adverse: "concern",
  unknown: "insufficient evidence",
};

function formatChoice(choice) {
  return choice.replaceAll("_", " ");
}

function renderChoiceDistribution(
  parent,
  probabilities,
  selectedChoice,
  choiceOrder = [],
) {
  const distribution = document.createElement("div");
  distribution.className = "choice-distribution";
  const availableChoices = Object.keys(probabilities || {});
  const orderedChoices = [
    ...choiceOrder.filter((choice) => availableChoices.includes(choice)),
    ...availableChoices.filter((choice) => !choiceOrder.includes(choice)),
  ];
  orderedChoices.forEach((choice) => {
    const probability = probabilities[choice];
    const row = document.createElement("div");
    row.className = `choice-row ${choiceTone[choice] || "unknown"}`;
    if (choice === selectedChoice) row.classList.add("selected");

    const label = document.createElement("div");
    addText(label, "span", "", formatChoice(choice));
    addText(label, "b", "", pct(probability));
    row.appendChild(label);

    const track = document.createElement("div");
    const fill = document.createElement("i");
    fill.style.width = pct(probability);
    track.appendChild(fill);
    row.appendChild(track);
    distribution.appendChild(row);
  });
  parent.appendChild(distribution);

  const key = document.createElement("div");
  key.className = "choice-key";
  const availableTones = new Set(
    orderedChoices.map((choice) => choiceTone[choice] || "unknown"),
  );
  ["favorable", "neutral", "adverse", "unknown"].forEach((tone) => {
    if (!availableTones.has(tone)) return;
    const item = document.createElement("span");
    item.className = tone;
    item.appendChild(document.createElement("i"));
    item.append(choiceToneLabel[tone]);
    key.appendChild(item);
  });
  parent.appendChild(key);
  addText(parent, "p", "distribution-note", "Bar length shows model probability");
}

function signalTile(container, label, type, value, options = {}) {
  const tile = document.createElement("article");
  tile.className = [
    options.probabilities ? "choice-signal" : "",
    options.wide ? "wide-signal" : "",
  ].filter(Boolean).join(" ");
  const heading = document.createElement("p");
  heading.className = "label";
  addText(heading, "span", "", label);
  addText(heading, "em", "", type);
  tile.appendChild(heading);

  const output = document.createElement("strong");
  output.textContent = value;
  if (options.suffix) {
    addText(output, "small", "", options.suffix);
  }
  tile.appendChild(output);
  if (options.probabilities) {
    renderChoiceDistribution(
      tile,
      options.probabilities,
      options.selected,
      options.choiceOrder,
    );
  }
  if (options.meter !== undefined) {
    addMeter(tile, options.meter, options.risk, options.meterLabels);
  }
  container.appendChild(tile);
}

function renderModelCard(modelKey, result) {
  const card = document.createElement("article");
  card.className = "model-card";
  const header = document.createElement("header");
  header.className = "model-card-head";
  const heading = document.createElement("div");
  addText(heading, "p", "", "Decision model");
  addText(heading, "h3", "", modelLabels[modelKey]);
  header.appendChild(heading);
  addText(
    header,
    "span",
    `runtime-chip ${result.runtime || "unavailable"}`,
    result.runtime || "unavailable",
  );
  card.appendChild(header);

  if (result.error) {
    const error = document.createElement("div");
    error.className = "model-error";
    addText(error, "h4", "", "Model unavailable");
    addText(error, "p", "", result.error);
    if (modelKey === "strands") {
      addText(
        error,
        "code",
        "",
        "./setup-strands.sh  →  ./run-strands.sh",
      );
    } else if (modelKey === "laya") {
      addText(
        error,
        "code",
        "",
        "./setup-laya.sh  →  ./run-laya.sh",
      );
    }
    card.appendChild(error);
    return card;
  }

  const scorecard = result.scorecard;
  const answers = result.answers;
  const scoreSection = document.createElement("section");
  scoreSection.className = "model-score";
  const ring = document.createElement("div");
  ring.className = "score-ring";
  ring.style.setProperty("--score-angle", `${scorecard.score * 3.6}deg`);
  const ringInner = document.createElement("div");
  addText(ringInner, "strong", "", String(scorecard.score));
  addText(ringInner, "span", "", "/ 100");
  ring.appendChild(ringInner);
  scoreSection.appendChild(ring);
  const posture = document.createElement("div");
  addText(posture, "p", "label", "Research posture");
  addText(posture, "h4", "", scorecard.posture);
  addText(
    posture,
    "p",
    "",
    "The score is based on customized business logic combining the following 5 factors.",
  );
  scoreSection.appendChild(posture);
  card.appendChild(scoreSection);

  const signals = document.createElement("div");
  signals.className = "model-signals";
  signalTile(
    signals,
    "Business momentum",
    "CHOICE · PROBABILITIES",
    answers.business_momentum.choice,
    {
      probabilities: answers.business_momentum.probabilities,
      selected: answers.business_momentum.choice,
      choiceOrder: ["improving", "stable", "deteriorating"],
    },
  );
  signalTile(
    signals,
    "Financial signal",
    "CHOICE · PROBABILITIES",
    answers.financial_signal.choice,
    {
      probabilities: answers.financial_signal.probabilities,
      selected: answers.financial_signal.choice,
      choiceOrder: ["positive", "mixed", "negative", "insufficient"],
    },
  );
  signalTile(
    signals,
    "Execution quality",
    "SCORE · 0–4",
    Number(answers.execution_quality.score).toFixed(1),
    {
      suffix: " / 4",
      meter: (answers.execution_quality.score / 4) * 100,
      meterLabels: ["0 · concerns", "4 · strong"],
    },
  );
  signalTile(
    signals,
    "Material risk",
    "NOUL · PROBABILITY",
    pct(answers.material_risk.noul),
    {
      meter: answers.material_risk.noul * 100,
      risk: true,
      meterLabels: ["0% · low risk", "100% · high risk"],
    },
  );
  signalTile(
    signals,
    "Thin coverage",
    "NOUL · PROBABILITY",
    pct(answers.thin_coverage.noul),
    {
      meter: answers.thin_coverage.noul * 100,
      risk: true,
      meterLabels: ["0% · sufficient", "100% · too thin"],
      wide: true,
    },
  );
  card.appendChild(signals);

  const meta = document.createElement("div");
  meta.className = "model-card-meta";
  const fields = [["Model", result.model]];
  fields.forEach(([label, value]) => {
    const item = document.createElement("span");
    item.append(`${label} `);
    addText(item, "b", "", value);
    meta.appendChild(item);
  });
  card.appendChild(meta);
  return card;
}

function addLatencyGroup(parent, title, fields) {
  const group = document.createElement("article");
  group.className = "latency-group";
  addText(group, "h3", "", title);
  const list = document.createElement("dl");
  fields.forEach(([label, value, key]) => {
    const row = document.createElement("div");
    addText(row, "dt", "", label);
    const output = addText(row, "dd", "", value);
    if (key) output.dataset.latency = key;
    list.appendChild(row);
  });
  group.appendChild(list);
  parent.appendChild(group);
}

function renderLatencyBreakdown(result, clientTimings) {
  const groups = document.querySelector("#latency-groups");
  groups.replaceChildren();
  const timings = result.timings || {};
  addLatencyGroup(groups, "Shared request", [
    ["Request parsing", duration(timings.request_parsing_ms)],
    ["News retrieval", duration(timings.news_retrieval_ms)],
    ["State preparation", duration(timings.state_preparation_ms)],
    ["Response preparation", duration(timings.response_preparation_ms)],
    ["Response serialization", duration(clientTimings.responseSerializationMs)],
    ["Server processing total", duration(clientTimings.serverProcessingMs)],
    [
      "Transport + browser parsing",
      duration(clientTimings.transportAndParsingMs),
    ],
    ["UI rendering", "Measuring…", "ui-render"],
    ["End to end", "Measuring…", "end-to-end"],
  ]);

  Object.entries(result.results).forEach(([modelKey, modelResult]) => {
    if (modelResult.error) return;
    addLatencyGroup(groups, modelLabels[modelKey], [
      ["Inference", duration(modelResult.inference_latency_ms)],
      ["Terminal logging", duration(modelResult.logging_latency_ms)],
      ["Business logic", duration(modelResult.business_logic_latency_ms)],
      ["Model pipeline total", duration(modelResult.model_pipeline_latency_ms)],
    ]);
  });
}

function updateRenderedTimings(uiRenderingMs, endToEndMs) {
  const uiRendering = document.querySelector('[data-latency="ui-render"]');
  const endToEnd = document.querySelector('[data-latency="end-to-end"]');
  if (uiRendering) uiRendering.textContent = duration(uiRenderingMs);
  if (endToEnd) endToEnd.textContent = duration(endToEndMs);
}

function renderArticles(articles) {
  const list = document.querySelector("#article-list");
  list.replaceChildren();
  articles.forEach((article, index) => {
    const row = document.createElement(article.url === "#" ? "div" : "a");
    row.className = "article";
    if (article.url !== "#") {
      row.href = article.url;
      row.target = "_blank";
      row.rel = "noreferrer";
    }
    addText(row, "span", "", String(index + 1).padStart(2, "0"));
    addText(row, "h3", "", article.title);
    addText(row, "span", "publisher", article.publisher);
    const date = document.createElement("time");
    date.textContent = new Intl.DateTimeFormat("en", {
      month: "short",
      day: "numeric",
    }).format(new Date(article.published));
    row.appendChild(date);
    list.appendChild(row);
  });
}

function render(result, clientTimings) {
  document.querySelector("#company-name").textContent = result.company;
  document.querySelector("#ticker-name").textContent = result.ticker || "NO TICKER";
  document.querySelector("#coverage-count").textContent =
    `${result.articles.length} article${result.articles.length === 1 ? "" : "s"}`;
  document.querySelector("#source-mode").textContent =
    result.news_mode === "live"
      ? "Live Google News RSS headlines"
      : "Fictional demonstration headlines";

  const modelResults = document.querySelector("#model-results");
  modelResults.replaceChildren();
  const entries = Object.entries(result.results);
  modelResults.classList.toggle("single", entries.length === 1);
  modelResults.classList.toggle("three", entries.length === 3);
  entries.forEach(([modelKey, modelResult]) => {
    modelResults.appendChild(renderModelCard(modelKey, modelResult));
  });
  renderLatencyBreakdown(result, clientTimings);
  renderArticles(result.articles);
  emptyDashboard.classList.add("hidden");
  dashboard.classList.remove("hidden");
  fetch("/api/status")
    .then((response) => response.json())
    .then(setStatus)
    .catch(() => {});
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  errorBox.textContent = "";
  button.disabled = true;
  button.querySelector("span").textContent = "Reading the week…";
  const endToEndStarted = performance.now();
  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        company: document.querySelector("#company").value.trim(),
        ticker: document.querySelector("#ticker").value.trim(),
        model_selection: document.querySelector("#model-selection").value,
        use_mock_news: document.querySelector("#mock-news").checked,
      }),
    });
    const result = await response.json();
    const roundTripMs = performance.now() - endToEndStarted;
    const serverProcessingMs =
      Number(response.headers.get("X-Server-Processing-Ms")) || 0;
    const clientTimings = {
      serverProcessingMs,
      responseSerializationMs:
        Number(response.headers.get("X-Response-Serialization-Ms")) || 0,
      transportAndParsingMs: Math.max(0, roundTripMs - serverProcessingMs),
    };
    if (!response.ok) {
      throw new Error(result.error || "Analysis failed.");
    }
    const renderingStarted = performance.now();
    render(result, clientTimings);
    requestAnimationFrame(() => {
      const renderedAt = performance.now();
      updateRenderedTimings(
        renderedAt - renderingStarted,
        renderedAt - endToEndStarted,
      );
    });
  } catch (error) {
    errorBox.textContent = error.message;
  } finally {
    button.disabled = false;
    button.querySelector("span").textContent = "Analyze last 7 days";
  }
});
