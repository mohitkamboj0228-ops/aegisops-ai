import { useCallback, useEffect, useState } from "react";
import "./App.css";
type Project = { id: string; name: string; url: string };
type Finding = {
  path: string;
  rule: string;
  severity: string;
  title: string;
  remediation: string;
};
type Scan = {
  id: string;
  project_id: string;
  created: string;
  score: number;
  status: string;
  summary: string;
  findings: Finding[];
};
type Incident = {
  id: string;
  project_id: string;
  title: string;
  severity: string;
  status: string;
};
type Plan = {
  id: string;
  status: string;
  scope: string;
  warning: string;
  files: Record<string, string>;
  changes: { path: string; diff: string }[];
};
type State = {
  projects: Project[];
  scans: Scan[];
  incidents: Incident[];
  ai?: { provider: string; model: string; configured: boolean };
  plans?: { id: string; scan_id: string; created: string; status: string }[];
  events?: { id: string; created: string; message: string }[];
};
const examples: Record<string, string> = {
  Dockerfile:
    'FROM python:latest\nWORKDIR /app\nCOPY . .\nCMD ["python", "app.py"]',
  "deployment.yaml":
    "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: demo\nspec:\n  template:\n    spec:\n      containers:\n        - name: app\n          image: demo:latest\n          securityContext:\n            privileged: true",
  "main.tf":
    'resource "aws_security_group" "demo" {\n  ingress {\n    from_port = 22\n    to_port = 22\n    protocol = "tcp"\n    cidr_blocks = ["0.0.0.0/0"]\n  }\n}',
};
async function api(path: string, body?: unknown) {
  const response = await fetch(
    "/api/" + path,
    body
      ? {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }
      : undefined,
  );
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "Request failed");
  return result;
}
function App() {
  const [state, setState] = useState<State>({
    projects: [],
    scans: [],
    incidents: [],
  });
  const [tab, setTab] = useState("Overview");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [project, setProject] = useState("");
  const [filename, setFilename] = useState("Dockerfile");
  const [source, setSource] = useState(examples.Dockerfile);
  const [selectedScan, setSelectedScan] = useState<Scan | null>(null);
  const [notice, setNotice] = useState("");
  const [aiResult, setAiResult] = useState<{
    scan_id: string;
    text: string;
    provider: string;
    model: string;
  } | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [reviewed, setReviewed] = useState(false);
  const [exportFiles, setExportFiles] = useState<Record<string, string> | null>(
    null,
  );
  const refresh = useCallback(async () => {
    try {
      setState(await api("state"));
      setError("");
    } catch (e) {
      setError(String(e));
    }
  }, []);
  useEffect(() => {
    void refresh();
  }, [refresh]);
  async function action(task: () => Promise<void>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await task();
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }
  const latest = selectedScan || state.scans[0];
  const open = state.incidents.filter((i) => i.status !== "resolved").length;
  const projectName = (id: string) =>
    state.projects.find((p) => p.id === id)?.name || "Project";
  return (
    <div className="shell">
      <aside>
        <a className="brand" href="#" onClick={() => setTab("Overview")}>
          <span className="logo">A</span>AegisOps<span className="ai">AI</span>
        </a>
        <p className="side-label">WORKSPACE / LOCAL</p>
        <nav>
          {["Overview", "Projects", "Policy scans", "Incidents"].map((t, i) => (
            <button
              key={t}
              className={tab === t ? "active" : ""}
              onClick={() => setTab(t)}
            >
              <span>{["◈", "▣", "⌁", "⚑"][i]}</span>
              {t}
              {t === "Incidents" && open > 0 && <b>{open}</b>}
            </button>
          ))}
        </nav>
        <div className="side-footer">
          <span className="dot" /> Policy engine online
          <small>Policy workspace · v2.0</small>
        </div>
      </aside>
      <main>
        <header>
          <span>
            Workspace <span className="muted">/ {tab}</span>
          </span>
          <span className="pill">LOCAL ENVIRONMENT</span>
        </header>
        <section className="content">
          <div className="page-title">
            <div>
              <p className="eyebrow">SECURE DELIVERY, EXPLAINED.</p>
              <h1>{tab === "Overview" ? "Your operations, in focus." : tab}</h1>
              <p className="muted">
                Inspect infrastructure policies. Track findings. Keep a clear
                audit history.
              </p>
            </div>
            <button className="primary" onClick={() => setTab("Policy scans")}>
              ＋ Run policy scan
            </button>
          </div>
          {error && (
            <div role="alert" className="alert">
              {error}
            </div>
          )}
          {notice && (
            <div role="status" className="notice">
              {notice}
            </div>
          )}
          {tab === "Overview" && (
            <>
              <div className="metrics">
                {[
                  ["Projects", state.projects.length, "Tracked repositories"],
                  [
                    "Policy scans",
                    state.scans.length,
                    "Persisted scan history",
                  ],
                  ["Open findings", open, "Across all recorded scans"],
                  [
                    "Latest policy score",
                    latest ? latest.score + " / 100" : "—",
                    "Heuristic · scanned text only",
                  ],
                ].map(([label, value, help]) => (
                  <article className="metric" key={label}>
                    <p>{label}</p>
                    <strong>{value}</strong>
                    <small>{help}</small>
                  </article>
                ))}
              </div>
              <div className="two-col">
                <article className="panel">
                  <div className="panel-head">
                    <h2>Recent policy runs</h2>
                    <span className="pill">LIVE DATA</span>
                  </div>
                  {state.scans.length === 0 ? (
                    <div className="empty">
                      <h3>Your first scan starts here</h3>
                      <p>
                        Add a project, then inspect a Dockerfile, Kubernetes
                        manifest or Terraform file.
                      </p>
                      <button onClick={() => setTab("Projects")}>
                        Add your first project →
                      </button>
                    </div>
                  ) : (
                    state.scans.slice(0, 6).map((s) => (
                      <button
                        className="run"
                        key={s.id}
                        onClick={() => {
                          setSelectedScan(s);
                          setTab("Policy scans");
                        }}
                      >
                        <span>
                          <strong>{projectName(s.project_id)}</strong>
                          <small>{new Date(s.created).toLocaleString()}</small>
                        </span>
                        <span className={"badge " + s.status}>{s.status}</span>
                        <b>{s.score}</b>
                      </button>
                    ))
                  )}
                </article>
                <article className="panel engine">
                  <span className="engine-symbol">⌁</span>
                  <h2>Explainable policy checks</h2>
                  <p>
                    Every finding includes a rule, severity and a suggested fix.
                  </p>
                  <ul>
                    <li>Container configuration</li>
                    <li>Kubernetes workload policies</li>
                    <li>Terraform risk indicators</li>
                    <li>Potential credential patterns</li>
                  </ul>
                  <div className="note">
                    Policy checks are deterministic. AI review:{" "}
                    {state.ai?.configured
                      ? `${state.ai.provider} configured`
                      : "not configured"}
                    . Automatic fixes update versioned workspace snapshots. Live
                    cloud resources are not modified.
                  </div>
                </article>
              </div>
            </>
          )}
          {tab === "Projects" && (
            <>
              <article className="panel">
                <h2>Connect project metadata</h2>
                <p className="muted">
                  Repository links are stored as references. Code is analyzed
                  only when you submit it.
                </p>
                <form
                  className="project-form"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void action(async () => {
                      const p = await api("projects", { name, url });
                      setProject(p.id);
                      setName("");
                      setUrl("");
                      setNotice(
                        "Project created. Open Policy scans to check a file.",
                      );
                    });
                  }}
                >
                  <label>
                    Project name
                    <input
                      required
                      maxLength={100}
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="e.g. Payment service"
                    />
                  </label>
                  <label>
                    GitHub repository (optional)
                    <input
                      type="url"
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                      placeholder="https://github.com/owner/repository"
                    />
                  </label>
                  <button className="primary" disabled={busy}>
                    Add project
                  </button>
                </form>
              </article>
              <div className="project-grid">
                {state.projects.map((p) => (
                  <article className="panel" key={p.id}>
                    <span className="eyebrow">REPOSITORY</span>
                    <h2>{p.name}</h2>
                    {p.url && (
                      <a href={p.url} target="_blank" rel="noreferrer">
                        View on GitHub ↗
                      </a>
                    )}
                    <p className="muted">
                      {state.scans.filter((s) => s.project_id === p.id).length}{" "}
                      policy runs
                    </p>
                    <button
                      onClick={() => {
                        setProject(p.id);
                        setTab("Policy scans");
                      }}
                    >
                      Inspect configuration →
                    </button>
                  </article>
                ))}
              </div>
            </>
          )}
          {tab === "Policy scans" && (
            <>
              <div className="note">
                Checks are text-based heuristics, not full parsers or
                vulnerability scanners. A passing result does not establish
                security or authorize deployment.
              </div>
              <article className="panel">
                <h2>Inspect a configuration file</h2>
                <div className="scan-controls">
                  <label>
                    Project
                    <select
                      value={project}
                      onChange={(e) => setProject(e.target.value)}
                    >
                      <option value="">Choose a project</option>
                      {state.projects.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    File type
                    <select
                      value={filename}
                      onChange={(e) => {
                        setFilename(e.target.value);
                        setSource(examples[e.target.value]);
                      }}
                    >
                      {Object.keys(examples).map((n) => (
                        <option key={n}>{n}</option>
                      ))}
                    </select>
                  </label>
                  <button
                    onClick={() => {
                      setSource(examples[filename]);
                      setNotice(
                        "Sample loaded. It is intentionally insecure for demonstration.",
                      );
                    }}
                  >
                    Load sample
                  </button>
                </div>
                <label className="editor-label">
                  File content
                  <textarea
                    spellCheck={false}
                    value={source}
                    onChange={(e) => setSource(e.target.value)}
                    maxLength={100000}
                  />
                </label>
                <div className="scan-footer">
                  <small>
                    Source snapshots are stored locally for remediation.
                    Detected credential-containing files are not retained.
                  </small>
                  <button
                    className="primary"
                    disabled={busy || !project || !source.trim()}
                    onClick={() =>
                      void action(async () => {
                        const result = await api("scans", {
                          project_id: project,
                          files: { [filename]: source },
                        });
                        setSelectedScan(result);
                        setPlan(null);
                        setReviewed(false);
                        setNotice(
                          "Scan completed. Findings and suggested fixes are ready.",
                        );
                      })
                    }
                  >
                    {busy ? "Checking…" : "Run policy checks →"}
                  </button>
                </div>
              </article>
              {latest && (
                <article className="panel">
                  <div className="panel-head">
                    <h2>Scan results · {projectName(latest.project_id)}</h2>
                    <span className={"badge " + latest.status}>
                      {latest.status} · {latest.score}/100
                    </span>
                  </div>
                  <p className="muted">{latest.summary}</p>
                  <div className="workflow-actions">
                    <button
                      disabled={busy || !state.ai?.configured}
                      onClick={() =>
                        void action(async () => {
                          const result = await api("ai/analyze", {
                            scan_id: latest.id,
                          });
                          setAiResult({ ...result, scan_id: latest.id });
                        })
                      }
                    >
                      Ask AI to review findings
                    </button>
                    <button
                      disabled={busy}
                      onClick={() =>
                        void action(async () => {
                          const result = await api("remediation/preview", {
                            scan_id: latest.id,
                          });
                          setPlan(result);
                          setReviewed(false);
                        })
                      }
                    >
                      Preview automatic fixes
                    </button>
                  </div>
                  <small>
                    AI receives fixed policy findings only, not file contents.
                    Provider usage may incur charges. Configuration does not
                    confirm model access.
                  </small>
                  {latest.findings.length === 0 ? (
                    <p className="notice">
                      No issues detected by the supported rules.
                    </p>
                  ) : (
                    latest.findings.map((f, i) => (
                      <div className="finding" key={i}>
                        <div>
                          <span className={"badge " + f.severity}>
                            {f.severity}
                          </span>
                          <code>
                            {f.rule} · {f.path}
                          </code>
                        </div>
                        <h3>{f.title}</h3>
                        <p>{f.remediation}</p>
                      </div>
                    ))
                  )}
                </article>
              )}
              {aiResult && latest?.id === aiResult.scan_id && (
                <article className="panel">
                  <h2>AI review · {aiResult.provider}</h2>
                  <small>{aiResult.model} · Advisory only</small>
                  <pre className="analysis-text">{aiResult.text}</pre>
                </article>
              )}
              {plan && (
                <article className="panel">
                  <h2>Review proposed configuration changes</h2>
                  <div className="note">
                    {plan.warning}
                    <br />
                    {plan.scope}
                  </div>
                  {plan.changes.map((change) => (
                    <div key={change.path}>
                      <h3>{change.path}</h3>
                      <pre className="diff">{change.diff}</pre>
                    </div>
                  ))}
                  <label className="check-label">
                    <input
                      type="checkbox"
                      checked={reviewed}
                      onChange={(e) => setReviewed(e.target.checked)}
                    />
                    I reviewed these changes and approve updating the workspace
                    snapshot.
                  </label>
                  <button
                    className="primary"
                    disabled={busy || !reviewed || plan.status !== "pending"}
                    onClick={() =>
                      void action(async () => {
                        const result = await api("remediation/apply", {
                          plan_id: plan.id,
                          approved: true,
                        });
                        setPlan({ ...plan, status: result.status });
                        setSelectedScan(result.scan);
                        setExportFiles(result.files);
                        setNotice(
                          "Fixes applied to a new workspace snapshot and rescanned. Your repository and live infrastructure were not changed.",
                        );
                      })
                    }
                  >
                    Apply reviewed fixes & rescan
                  </button>
                </article>
              )}
              {exportFiles && (
                <article className="panel">
                  <h2>Updated configuration</h2>
                  <p className="muted">
                    Download the workspace snapshot as JSON. Review and test the
                    files before deploying them.
                  </p>
                  <button
                    onClick={() => {
                      const blob = new Blob(
                        [JSON.stringify(exportFiles, null, 2)],
                        { type: "application/json" },
                      );
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement("a");
                      a.href = url;
                      a.download = "aegisops-configuration.json";
                      a.click();
                      URL.revokeObjectURL(url);
                    }}
                  >
                    Download configuration snapshot
                  </button>
                </article>
              )}
              {!!state.plans?.length && (
                <article className="panel">
                  <h2>Remediation history</h2>
                  {state.plans.map((p) => (
                    <div className="run" key={p.id}>
                      <span>
                        <code>{p.id.slice(0, 12)}</code>
                        <small>{new Date(p.created).toLocaleString()}</small>
                      </span>
                      <span className="badge">{p.status}</span>
                      {p.status === "applied" && (
                        <button
                          disabled={busy}
                          onClick={() =>
                            void action(async () => {
                              const result = await api("remediation/rollback", {
                                plan_id: p.id,
                                approved: true,
                              });
                              setSelectedScan(result.scan);
                              setExportFiles(result.files);
                              setPlan(null);
                              setNotice(
                                "Original workspace configuration restored as a new snapshot and rescanned.",
                              );
                            })
                          }
                        >
                          Restore original snapshot
                        </button>
                      )}
                    </div>
                  ))}
                </article>
              )}
              {!!state.events?.length && (
                <article className="panel">
                  <h2>Audit events</h2>
                  {state.events.slice(0, 10).map((e) => (
                    <div className="finding" key={e.id}>
                      <small>{new Date(e.created).toLocaleString()}</small>
                      <p>{e.message}</p>
                    </div>
                  ))}
                </article>
              )}
              {state.scans.length > 0 && (
                <article className="panel">
                  <h2>Scan history</h2>
                  {state.scans.map((s) => (
                    <button
                      className="run"
                      key={s.id}
                      onClick={() => {
                        setSelectedScan(s);
                        setPlan(null);
                        setReviewed(false);
                      }}
                    >
                      <span>
                        {projectName(s.project_id)}
                        <small>{new Date(s.created).toLocaleString()}</small>
                      </span>
                      <span className={"badge " + s.status}>{s.status}</span>
                      <b>{s.score}</b>
                    </button>
                  ))}
                </article>
              )}
            </>
          )}
          {tab === "Incidents" && (
            <article className="panel">
              <h2>Finding lifecycle</h2>
              <p className="muted">
                Each scan records its own findings. Resolving a finding records
                your review; it does not modify infrastructure.
              </p>
              {!state.incidents.length ? (
                <div className="empty">
                  No findings yet. Run a policy scan to get started.
                </div>
              ) : (
                state.incidents.map((i) => (
                  <div className="incident" key={i.id}>
                    <span className={"badge " + i.severity}>{i.severity}</span>
                    <div>
                      <strong>{i.title}</strong>
                      <small>{projectName(i.project_id)}</small>
                    </div>
                    <label className="sr-only" htmlFor={i.id}>
                      Status for {i.title}
                    </label>
                    <select
                      id={i.id}
                      value={i.status}
                      disabled={busy}
                      onChange={(e) =>
                        void action(async () => {
                          await api("incidents/status", {
                            id: i.id,
                            status: e.target.value,
                          });
                        })
                      }
                    >
                      {["open", "acknowledged", "resolved"].map((s) => (
                        <option key={s}>{s}</option>
                      ))}
                    </select>
                  </div>
                ))
              )}
            </article>
          )}
          <footer>
            AegisOps AI{" "}
            <span>Local policy workspace · No cloud credentials required</span>
          </footer>
        </section>
      </main>
    </div>
  );
}
export default App;
