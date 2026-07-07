import { useEffect, useMemo, useState, type FormEvent } from "react";
import type { Method, ModelStatus } from "../types";
import { METHOD_SHORT } from "../types";
import type { AnalyzePayload } from "../api";
import { SAMPLE_INCIDENTS } from "../sampleIncidents";
import { CheckIcon } from "./icons";

const METHODS: { v: Method; icon: string; detail: string }[] = [
  { v: "five_why", icon: "5", detail: "Linear causal chain" },
  { v: "fishbone", icon: "F", detail: "Cause categories" },
  { v: "fault_tree", icon: "T", detail: "Event logic tree" },
];

const SEVERITIES = [
  { value: "low", label: "Low", color: "bg-att-400" },
  { value: "medium", label: "Medium", color: "bg-warn-500" },
  { value: "high", label: "High", color: "bg-danger-500" },
  { value: "critical", label: "Critical", color: "bg-danger-700" },
];

function labelForSeverity(value: string | null) {
  if (!value) return "Not set";
  return SEVERITIES.find((s) => s.value === value)?.label ?? value;
}

export default function AnalysisForm({
  onSubmit,
  busy,
  memoryRecordCount,
  memoryEnabled = true,
  writerModel,
  validatorModel,
  validationEnabled,
  allowedWriterModels = [],
  allowedValidatorModels = [],
  modelStatus,
}: {
  onSubmit: (p: AnalyzePayload) => void;
  busy: boolean;
  memoryRecordCount?: number | null;
  memoryEnabled?: boolean;
  writerModel: string;
  validatorModel: string;
  validationEnabled: boolean;
  allowedWriterModels?: string[];
  allowedValidatorModels?: string[];
  modelStatus?: ModelStatus | null;
}) {
  const [problem, setProblem] = useState("");
  const [method, setMethod] = useState<Method>("five_why");
  const [compareOn, setCompareOn] = useState(false);
  const [compareMethod, setCompareMethod] = useState<Method>("fishbone");
  const [severity, setSeverity] = useState<string | null>(null);
  const [systemArea, setSystemArea] = useState("");
  const [context, setContext] = useState("");
  const [selectedExample, setSelectedExample] = useState("");
  const modelOptions = useMemo(
    () => Array.from(new Set(allowedWriterModels.filter(Boolean))),
    [allowedWriterModels],
  );
  const [generationModel, setGenerationModel] = useState(writerModel);
  const validatorOptions = useMemo(
    () => Array.from(new Set(allowedValidatorModels.filter(Boolean))),
    [allowedValidatorModels],
  );
  const [validationModel, setValidationModel] = useState(validatorModel);
  const availability = useMemo(() => {
    const pairs = modelStatus?.writer.allowed_models ?? [];
    return new Map(pairs.map((item) => [item.model, item.available]));
  }, [modelStatus]);
  const validatorAvailability = useMemo(() => {
    const pairs = modelStatus?.validator.allowed_models ?? [];
    return new Map(pairs.map((item) => [item.model, item.available]));
  }, [modelStatus]);

  const effectiveCompare = useMemo(
    () => compareMethod === method ? METHODS.find((m) => m.v !== method)!.v : compareMethod,
    [compareMethod, method],
  );

  useEffect(() => {
    if (!generationModel || !modelOptions.includes(generationModel)) {
      setGenerationModel(modelOptions.includes(writerModel) ? writerModel : modelOptions[0] || "");
    }
  }, [generationModel, modelOptions, writerModel]);

  useEffect(() => {
    if (!validationModel || !validatorOptions.includes(validationModel)) {
      setValidationModel(validatorOptions.includes(validatorModel) ? validatorModel : validatorOptions[0] || "");
    }
  }, [validationModel, validatorOptions, validatorModel]);

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    onSubmit({
      problem_statement: problem.trim(),
      method,
      compare_method: compareOn && effectiveCompare !== method ? effectiveCompare : null,
      severity,
      system_area: systemArea.trim() || null,
      context: context.trim() || null,
      generation_model: generationModel || null,
      validation_model: validationEnabled ? validationModel || null : null,
    });
  }

  function loadExample(id: string) {
    setSelectedExample(id);
    const sample = SAMPLE_INCIDENTS.find((item) => item.id === id);
    if (!sample) return;
    setProblem(sample.problem);
    setContext(sample.context);
    setSeverity(sample.severity);
    setSystemArea(sample.systemArea);
    setMethod(sample.method);
    setCompareOn(Boolean(sample.compareMethod));
    if (sample.compareMethod) setCompareMethod(sample.compareMethod);
  }

  const methodControl = (selected: Method, setSelected: (m: Method) => void, disabled?: Method) => (
    <div className="grid gap-2 sm:grid-cols-3">
      {METHODS.map((m) => {
        const off = disabled === m.v;
        const on = selected === m.v;
        return (
          <button
            type="button"
            key={m.v}
            disabled={off}
            onClick={() => setSelected(m.v)}
            className={`min-h-[72px] rounded-lg border px-3 py-3 text-left transition ${
              on
                ? "border-primary bg-primary-tint text-primary-selected ring-2 ring-primary-soft"
                : "border-slate-200 bg-white text-ink-soft hover:border-primary-soft hover:bg-primary-tint"
            } ${off ? "cursor-not-allowed opacity-40" : ""}`}
          >
            <span className="flex items-center gap-2">
              <span className={`grid h-7 w-7 place-items-center rounded-md text-ui font-extrabold ${
                on ? "bg-primary text-white" : "bg-slate-100 text-ink"
              }`}>
                {m.icon}
              </span>
              <span className="text-body-sm font-extrabold">{METHOD_SHORT[m.v]}</span>
            </span>
            <span className="mt-1 block text-ui font-semibold leading-4 opacity-75">{m.detail}</span>
          </button>
        );
      })}
    </div>
  );

  const memoryLabel = memoryEnabled
    ? memoryRecordCount != null ? `${memoryRecordCount} records` : "Checking"
    : "Disabled";
  const canSubmit = problem.trim().length >= 10 && Boolean(generationModel);

  return (
    <form onSubmit={submit} className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
      <section className="rounded-lg border border-slate-200 bg-white shadow-card">
        <div className="border-b border-slate-200 px-5 py-5 sm:px-6">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-caption font-extrabold uppercase tracking-[0.14em] text-primary-selected">New Analysis</p>
              <h1 className="mt-1 text-title font-extrabold leading-tight tracking-tight text-ink">Create RCA Draft</h1>
              <p className="mt-2 max-w-[760px] text-body leading-6 text-ink-soft">
                Describe the incident, choose an RCA method, and generate local PDF, HTML, and supporting artifacts.
              </p>
            </div>
            <div className="rounded-md border border-primary-soft bg-primary-tint px-3 py-2 text-ui font-bold text-primary-selected">
              Outputs local
            </div>
          </div>
        </div>

        <div className="space-y-5 px-5 py-5 sm:px-6">
          <div>
            <div className="mb-2 flex flex-wrap items-end justify-between gap-3">
              <label className="block text-body-sm font-semibold text-ink" htmlFor="problem">Problem statement</label>
              <div className="min-w-[240px]">
                <label className="mb-1 block text-caption font-extrabold uppercase tracking-[0.12em] text-ink-muted" htmlFor="sample-incident">
                  Load example incident
                </label>
                <select
                  id="sample-incident"
                  value={selectedExample}
                  onChange={(e) => loadExample(e.target.value)}
                  className="h-10 w-full rounded-md border border-primary-soft bg-white px-3 text-ui font-semibold text-ink-soft outline-none transition hover:border-primary"
                >
                  <option value="">Choose a demo-ready incident</option>
                  {SAMPLE_INCIDENTS.map((sample) => (
                    <option key={sample.id} value={sample.id}>{sample.label}</option>
                  ))}
                </select>
              </div>
            </div>
            <textarea
              id="problem"
              value={problem}
              onChange={(e) => {
                setProblem(e.target.value);
                setSelectedExample("");
              }}
              required
              maxLength={6000}
              placeholder="What happened, when it started, who or what is impacted, and what changed recently?"
              className="min-h-[148px] w-full resize-y rounded-lg border border-slate-300 bg-slate-50 px-3 py-3 text-body leading-relaxed text-ink outline-none transition focus:border-primary focus:bg-white focus:ring-[3px] focus:ring-primary-tint"
            />
            <div className="mt-1.5 flex justify-between gap-3 text-ui text-ink-muted">
              <span>Supporting facts are treated as data, not instructions.</span>
              <span>{problem.length} / 6000</span>
            </div>
          </div>

          <div>
            <label className="mb-1.5 block text-body-sm font-semibold text-ink" htmlFor="context">Supporting context</label>
            <textarea
              id="context"
              value={context}
              onChange={(e) => setContext(e.target.value)}
              placeholder="Paste logs, timeline, recent changes, metrics, or constraints that should inform the RCA."
              className="min-h-[108px] w-full resize-y rounded-lg border border-slate-300 bg-slate-50 px-3 py-3 text-body leading-relaxed text-ink outline-none transition focus:border-primary focus:bg-white focus:ring-[3px] focus:ring-primary-tint"
            />
          </div>

          <div>
            <div className="mb-2 flex items-center justify-between gap-3">
              <label className="text-body-sm font-semibold text-ink">RCA method</label>
              <span className="text-ui font-semibold text-ink-muted">Method-specific report visuals are generated after analysis.</span>
            </div>
            {methodControl(method, setMethod)}
          </div>

          <div>
            <label className="mb-1.5 block text-body-sm font-semibold text-ink" htmlFor="generation-model">Writer model</label>
            <select
              id="generation-model"
              value={generationModel}
              onChange={(e) => setGenerationModel(e.target.value)}
              className="h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-body font-semibold text-ink outline-none transition focus:border-primary focus:bg-white focus:ring-[3px] focus:ring-primary-tint"
            >
              {!modelOptions.length && <option value="">No allowlisted models configured</option>}
              {modelOptions.map((model) => {
                const available = availability.get(model);
                return (
                  <option key={model} value={model} disabled={available === false}>
                    {model}{available === false ? " (not pulled)" : available === true ? " (ready)" : ""}
                  </option>
                );
              })}
            </select>
            <p className="mt-1.5 text-ui leading-5 text-ink-muted">
              Only allowlisted local writer models can be selected for this run.
            </p>
          </div>

          {validationEnabled && (
            <div>
              <label className="mb-1.5 block text-body-sm font-semibold text-ink" htmlFor="validation-model">Validator model</label>
              <select
                id="validation-model"
                value={validationModel}
                onChange={(e) => setValidationModel(e.target.value)}
                className="h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-body font-semibold text-ink outline-none transition focus:border-primary focus:bg-white focus:ring-[3px] focus:ring-primary-tint"
              >
                {validatorOptions.map((model) => {
                  const available = validatorAvailability.get(model);
                  return (
                    <option key={model} value={model} disabled={available === false}>
                      {model}{available === false ? " (not pulled)" : available === true ? " (ready)" : ""}
                    </option>
                  );
                })}
              </select>
              <p className="mt-1.5 text-ui leading-5 text-ink-muted">
                Reviewer model that assigns final confidence and validation notes.
              </p>
            </div>
          )}

          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
            <div>
              <label className="mb-1.5 block text-body-sm font-semibold text-ink">Severity</label>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-2">
                {SEVERITIES.map((s) => {
                  const on = severity === s.value;
                  return (
                    <button
                      type="button"
                      key={s.value}
                      onClick={() => setSeverity(on ? null : s.value)}
                      className={`flex h-10 items-center gap-2 rounded-md border px-3 text-left text-ui font-bold transition ${
                        on ? "border-primary bg-primary-tint text-primary-selected ring-2 ring-primary-soft" : "border-slate-200 bg-white text-ink-soft hover:border-primary-soft"
                      }`}
                    >
                      <span className={`h-2.5 w-2.5 rounded-full ${s.color}`} />
                      {s.label}
                    </button>
                  );
                })}
              </div>
            </div>
            <div>
              <label className="mb-1.5 block text-body-sm font-semibold text-ink" htmlFor="system-area">System area</label>
              <input
                id="system-area"
                type="text"
                value={systemArea}
                onChange={(e) => setSystemArea(e.target.value)}
                placeholder="Optional"
                className="h-10 w-full rounded-md border border-slate-300 bg-slate-50 px-3 text-body text-ink outline-none transition focus:border-primary focus:bg-white focus:ring-[3px] focus:ring-primary-tint"
              />
            </div>
          </div>

          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <button
              type="button"
              onClick={() => setCompareOn(!compareOn)}
              className="flex w-full items-center justify-between gap-3 text-left"
            >
              <span>
                <span className="block text-body-sm font-semibold text-ink">Compare methods</span>
                <span className="block text-ui text-ink-muted">Run a second RCA method side by side.</span>
              </span>
              <span className={`relative h-6 w-11 flex-shrink-0 rounded-full transition ${compareOn ? "bg-primary-hover" : "bg-slate-300"}`}>
                <span className={`absolute top-1 h-4 w-4 rounded-full bg-white shadow transition-all ${compareOn ? "left-6" : "left-1"}`} />
              </span>
            </button>
            {compareOn && (
              <div className="mt-4">
                <label className="mb-2 block text-ui font-semibold text-ink">Second method</label>
                {methodControl(effectiveCompare, setCompareMethod, method)}
              </div>
            )}
          </div>
        </div>
      </section>

      <aside className="rounded-lg border border-slate-200 bg-white shadow-card xl:sticky xl:top-[84px]">
        <div className="border-b border-slate-200 px-5 py-4">
          <p className="text-caption font-extrabold uppercase tracking-[0.14em] text-ink-muted">Run Summary</p>
          <h2 className="mt-1 text-section font-extrabold text-ink">Draft configuration</h2>
        </div>
        <div className="space-y-4 p-5">
          {[
            ["Method", METHOD_SHORT[method]],
            ["Severity", labelForSeverity(severity)],
            ["System area", systemArea.trim() || "Not set"],
            ["Writer model", generationModel || writerModel],
            ["Validator", validationEnabled ? validationModel || validatorModel : "Off"],
            ["Memory", memoryLabel],
          ].map(([label, value]) => (
            <div key={label} className="grid grid-cols-[112px_minmax(0,1fr)] gap-3 text-body-sm">
              <span className="font-bold text-ink-muted">{label}</span>
              <span className="min-w-0 break-words font-extrabold text-ink">{value}</span>
            </div>
          ))}

          <div className="border-t border-slate-200 pt-4">
            <p className="mb-3 text-ui font-extrabold uppercase tracking-[0.12em] text-ink-muted">Expected outputs</p>
            <div className="space-y-2">
              {["HTML web report", "PDF printable report", "Matching past RCA Excel workbook"].map((item) => (
                <div key={item} className="flex items-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
                  <span className="grid h-5 w-5 place-items-center rounded-full bg-primary-soft text-primary-selected"><CheckIcon className="h-3.5 w-3.5" /></span>
                  <span className="text-ui font-bold text-ink-soft">{item}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-primary-soft bg-primary-tint px-4 py-3">
            <p className="text-body-sm font-extrabold text-primary-selected">Local-first by design</p>
            <p className="mt-1 text-ui leading-5 text-primary-selected">
              Analysis runs against the configured model provider. Outputs are written locally and the model server must be available.
            </p>
          </div>

          <button
            type="submit"
            disabled={busy || !canSubmit}
            className="flex h-11 w-full items-center justify-center gap-2 rounded-md bg-primary px-4 text-body font-extrabold text-white shadow-[0_14px_28px_-18px_rgba(0,159,219,.75)] transition hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-60"
          >
            {busy && <span className="h-4 w-4 animate-spin rounded-full border-[2.5px] border-white/40 border-t-white" />}
            {busy ? "Starting analysis" : "Generate RCA"}
          </button>
        </div>
      </aside>
    </form>
  );
}
