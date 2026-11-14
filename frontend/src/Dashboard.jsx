
import { useEffect, useState } from "react";
import {
  Activity,
  Server,
  AlertTriangle,
  ShieldCheck,
  ShieldAlert,
  Cpu,
  MemoryStick,
  HardDrive,
  Brain,
  LayoutDashboard,
  FileText,
  Settings,
  RefreshCw,
  Mail,
  Globe,
  Clock,
  ExternalLink,
  CheckCircle,
  XCircle,
} from "lucide-react";

import {
  getHeartbeat,
  getAgentStatus,
  getIncidents,
  getInvestigations,
  getSecurityAlerts,
  getSecuritySummary,
  getWebsites,
  getWebsiteHistory,
  getRemoteServers,
} from "./api";

function Dashboard() {
  const [heartbeat, setHeartbeat] = useState(null);
  const [agentStatus, setAgentStatus] = useState("unknown");
  const [incidents, setIncidents] = useState([]);
  const [investigations, setInvestigations] = useState([]);
  const [securityAlerts, setSecurityAlerts] = useState([]);
  const [securitySummary, setSecuritySummary] = useState({});

  const [websites, setWebsites] = useState([]);
  const [websiteSummary, setWebsiteSummary] = useState({});
  const [websiteHistory, setWebsiteHistory] = useState([]);

  const [remoteServers, setRemoteServers] = useState([]);
  const [remoteServerSummary, setRemoteServerSummary] = useState({});

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadDashboard() {
    try {
      const [
        heartbeatData,
        statusData,
        incidentData,
        investigationData,
        alertData,
        summaryData,
        websiteData,
        websiteHistoryData,
        remoteServersData,
      ] = await Promise.all([
        getHeartbeat(),
        getAgentStatus(),
        getIncidents(),
        getInvestigations(),
        getSecurityAlerts(),
        getSecuritySummary(),
        getWebsites(),
        getWebsiteHistory(),
        getRemoteServers(),
      ]);

      setHeartbeat(heartbeatData.metrics ? heartbeatData : null);
      setAgentStatus(statusData.status);
      setIncidents(incidentData.incidents || []);
      setInvestigations(investigationData.investigations || []);
      setSecurityAlerts(alertData.alerts || []);
      setSecuritySummary(summaryData || {});

      setWebsites(websiteData.websites || []);
      setWebsiteSummary(websiteData || {});
      setWebsiteHistory(websiteHistoryData.history || []);

      setRemoteServers(remoteServersData.servers || []);
      setRemoteServerSummary(remoteServersData || {});

      setError("");
    } catch (err) {
      setError(
        "Unable to load dashboard data. Check backend connection and API endpoints."
      );
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDashboard();

    const interval = setInterval(loadDashboard, 5000);

    return () => clearInterval(interval);
  }, []);

  const metrics = heartbeat?.metrics || {};

  const latestRemoteServers = remoteServers;

  // Calculate current remote server counts from heartbeat timestamps.
  function isRemoteServerOnline(server) {
    if (!server.last_heartbeat || server.status !== "ONLINE") {
      return false;
    }

    // Backend SQLite timestamps are UTC without a timezone suffix.
    const heartbeatDate = new Date(
      `${server.last_heartbeat.replace(" ", "T")}Z`
    );

    const heartbeatAgeMs = Date.now() - heartbeatDate.getTime();

    return (
      Number.isFinite(heartbeatAgeMs) &&
      heartbeatAgeMs >= -5000 &&
      heartbeatAgeMs <= 30000
    );
  }

  const remoteOnlineCount = latestRemoteServers.filter(
    isRemoteServerOnline
  ).length;

  const remoteOfflineCount =
    latestRemoteServers.length - remoteOnlineCount;

  const openIncidents = incidents.filter(
    (incident) => incident.status === "OPEN"
  ).length;

  const systemHealthy =
    agentStatus === "online" &&
    heartbeat?.health?.status === "healthy" &&
    openIncidents === 0;

  const stats = [
    {
      title: "System Status",
      value: systemHealthy ? "Healthy" : "Attention",
      icon: ShieldCheck,
      color: "green",
    },
    {
      title: "Active Incidents",
      value: openIncidents,
      icon: AlertTriangle,
      color: "red",
    },
    {
      title: "AI Investigations",
      value: investigations.length,
      icon: Brain,
      color: "purple",
    },
    {
      title: "Production Agent",
      value: agentStatus.toUpperCase(),
      icon: Server,
      color: "blue",
    },
  ];

  const securityStats = [
    {
      title: "Total Security Alerts",
      value: securitySummary.total_alerts ?? 0,
      icon: ShieldAlert,
      color: "blue",
    },
    {
      title: "Critical Alerts",
      value: securitySummary.critical_alerts ?? 0,
      icon: AlertTriangle,
      color: "red",
    },
    {
      title: "High Severity",
      value: securitySummary.high_alerts ?? 0,
      icon: ShieldAlert,
      color: "red",
    },
    {
      title: "Medium Severity",
      value: securitySummary.medium_alerts ?? 0,
      icon: Activity,
      color: "purple",
    },
    {
      title: "Emails Sent",
      value: securitySummary.emails_sent ?? 0,
      icon: Mail,
      color: "green",
    },
  ];

  const websiteStats = [
    {
      title: "Total Websites",
      value: websiteSummary.total_websites ?? 0,
      icon: Globe,
      color: "blue",
    },
    {
      title: "Websites Online",
      value: websiteSummary.up ?? 0,
      icon: CheckCircle,
      color: "green",
    },
    {
      title: "Websites Offline",
      value: websiteSummary.down ?? 0,
      icon: XCircle,
      color: "red",
    },
  ];

  function formatDate(date) {
    if (!date) return "N/A";
    return new Date(date).toLocaleString();
  }

  function getSeverityClass(severity) {
    switch (severity?.toUpperCase()) {
      case "CRITICAL":
        return "critical";
      case "HIGH":
        return "high";
      case "MEDIUM":
        return "medium";
      case "LOW":
        return "low";
      default:
        return "";
    }
  }

  function getWebsiteStatusClass(status) {
    return status === "UP" ? "online-label" : "offline-label";
  }

  function getWebsiteStatusIcon(status) {
    return status === "UP" ? (
      <CheckCircle size={17} />
    ) : (
      <XCircle size={17} />
    );
  }

  return (
    <div className="dashboard">
      <aside className="sidebar">
        <h2>🛡 SentinelAI</h2>
        <p className="sidebar-subtitle">Multi-Agent Monitoring</p>

        <nav>
          <a className="active">
            <LayoutDashboard size={18} /> Dashboard
          </a>
          <a>
            <Activity size={18} /> Monitoring
          </a>
          <a>
            <Globe size={18} /> Website Monitoring
          </a>
          <a>
            <AlertTriangle size={18} /> Incidents
          </a>
          <a>
            <ShieldAlert size={18} /> Security Alerts
          </a>
          <a>
            <Brain size={18} /> AI Investigations
          </a>
          <a>
            <FileText size={18} /> Reports
          </a>
          <a>
            <Settings size={18} /> Settings
          </a>
        </nav>

        <div className="agent-status">
          <span className="status-dot"></span>
          Development Agent Online
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <h1>Production Overview</h1>
            <p>
              Monitor, investigate and manage production incidents.
            </p>
          </div>

          <div className="live-badge">
            <span className="status-dot"></span>
            LIVE MONITORING
          </div>
        </header>

        {error && <p className="error-message">{error}</p>}

        {/* PRODUCTION STATISTICS */}
        <section className="stats-grid">
          {stats.map((item) => {
            const Icon = item.icon;

            return (
              <div className="stat-card" key={item.title}>
                <div className={`stat-icon ${item.color}`}>
                  <Icon size={23} />
                </div>

                <div>
                  <p>{item.title}</p>
                  <h2>{item.value}</h2>
                </div>
              </div>
            );
          })}
        </section>

        {/* PRODUCTION MONITORING */}
        <section className="monitor-grid">
          <div className="panel">
            <h3>Production Agent</h3>

            <div className="agent-card">
              <Server size={30} />

              <div>
                <h4>SentinelAI Production Agent</h4>
                <p>
                  {agentStatus === "online"
                    ? "Heartbeat monitoring active"
                    : "Waiting for production heartbeat"}
                </p>
              </div>

              <span
                className={
                  agentStatus === "online"
                    ? "online-label"
                    : "offline-label"
                }
              >
                {agentStatus.toUpperCase()}
              </span>
            </div>

            <p className="last-seen">
              Last heartbeat: {formatDate(metrics.timestamp)}
            </p>
          </div>

          <div className="panel">
            <h3>System Resources</h3>

            {[
              {
                name: "CPU Usage",
                value: metrics.cpu_percent,
                icon: Cpu,
              },
              {
                name: "RAM Usage",
                value: metrics.ram_percent,
                icon: MemoryStick,
              },
              {
                name: "Disk Usage",
                value: metrics.disk_percent,
                icon: HardDrive,
              },
            ].map((resource) => {
              const Icon = resource.icon;
              const value = Number(resource.value);

              const validValue = Number.isFinite(value)
                ? Math.min(100, Math.max(0, value))
                : 0;

              return (
                <div key={resource.name}>
                  <div className="resource">
                    <span>
                      <Icon size={17} /> {resource.name}
                    </span>

                    <strong>
                      {Number.isFinite(value)
                        ? `${value.toFixed(1)}%`
                        : "N/A"}
                    </strong>
                  </div>

                  <div className="progress">
                    <div style={{ width: `${validValue}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* REMOTE SERVER MONITORING */}
        <section className="panel incident-panel">
          <h3>
            <Server size={19} /> Remote Servers
          </h3>

          <p className="last-seen">
            {latestRemoteServers.length} total
            {" · "}
            {remoteOnlineCount} online
            {" · "}
            {remoteOfflineCount} offline
          </p>

          {loading ? (
            <p>Loading remote server data...</p>
          ) : latestRemoteServers.length === 0 ? (
            <p>No remote servers registered yet.</p>
          ) : (
            <div className="website-grid">
              {latestRemoteServers.map((event) => {
                const server = event.payload || {};

                const cpu = Number(server.cpu_usage);
                const ram = Number(server.ram_usage);
                const disk = Number(server.disk_usage);

                const isOnline = isRemoteServerOnline(event);

                const hasWarning =
                  (Number.isFinite(cpu) && cpu >= 85) ||
                  (Number.isFinite(ram) && ram >= 85) ||
                  (Number.isFinite(disk) && disk >= 90) ||
                  server.health_status === "WARNING";

                const resources = [
                  { name: "CPU Usage", value: cpu },
                  { name: "RAM Usage", value: ram },
                  { name: "Disk Usage", value: disk },
                ];

                return (
                  <div
                    className="website-card"
                    key={event.server_name}
                  >
                    <div className="website-card-header">
                      <div className="website-icon">
                        <Server size={22} />
                      </div>

                      <span
                        className={
                          isOnline ? "online-label" : "offline-label"
                        }
                      >
                        {isOnline ? "ONLINE" : "OFFLINE"}
                      </span>
                    </div>

                    <h4>{event.server_name || "Unknown server"}</h4>

                    <p className="website-url">
                      {server.operating_system || "Windows"}
                    </p>

                    <div className="website-details">
                      {resources.map((resource) => {
                        const valid = Number.isFinite(resource.value);

                        const width = valid
                          ? Math.min(
                              100,
                              Math.max(0, resource.value)
                            )
                          : 0;

                        return (
                          <div key={resource.name}>
                            <span>{resource.name}</span>

                            <strong>
                              {valid
                                ? `${resource.value.toFixed(1)}%`
                                : "N/A"}
                            </strong>

                            <div className="progress">
                              <div
                                style={{ width: `${width}%` }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    <p className="website-last-check">
                      <Clock size={13} />
                      Last heartbeat: {formatDate(event.last_heartbeat)}
                    </p>

                    <p
                      className={
                        hasWarning ? "offline-label" : "online-label"
                      }
                    >
                      {hasWarning
                        ? "Resource attention required"
                        : "Resources normal"}
                    </p>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* WEBSITE MONITORING OVERVIEW */}
        <section className="panel">
          <h3>
            <Globe size={19} /> Website Monitoring Overview
          </h3>

          <section className="stats-grid">
            {websiteStats.map((item) => {
              const Icon = item.icon;

              return (
                <div className="stat-card" key={item.title}>
                  <div className={`stat-icon ${item.color}`}>
                    <Icon size={23} />
                  </div>

                  <div>
                    <p>{item.title}</p>
                    <h2>{item.value}</h2>
                  </div>
                </div>
              );
            })}
          </section>
        </section>

        {/* WEBSITE STATUS CARDS */}
        <section className="panel incident-panel">
          <h3>
            <Globe size={19} /> Monitored Websites
          </h3>

          {loading ? (
            <p>Loading website status...</p>
          ) : websites.length === 0 ? (
            <p>No website monitoring data available yet.</p>
          ) : (
            <div className="website-grid">
              {websites.map((website) => (
                <div className="website-card" key={website.url}>
                  <div className="website-card-header">
                    <div className="website-icon">
                      <Globe size={22} />
                    </div>

                    <span
                      className={getWebsiteStatusClass(website.status)}
                    >
                      {getWebsiteStatusIcon(website.status)}
                      {website.status}
                    </span>
                  </div>

                  <h4>{website.website_name}</h4>

                  <a
                    href={website.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="website-url"
                  >
                    {website.url}
                    <ExternalLink size={13} />
                  </a>

                  <div className="website-details">
                    <div>
                      <span>HTTP Status</span>
                      <strong>{website.status_code ?? "N/A"}</strong>
                    </div>

                    <div>
                      <span>Response Time</span>
                      <strong>
                        {website.response_time_ms != null
                          ? `${website.response_time_ms} ms`
                          : "N/A"}
                      </strong>
                    </div>
                  </div>

                  {website.error && (
                    <p className="website-error">
                      Error: {website.error}
                    </p>
                  )}

                  <p className="website-last-check">
                    <Clock size={13} />
                    Last checked: {formatDate(website.checked_at)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* WEBSITE MONITORING HISTORY */}
        <section className="panel incident-panel">
          <h3>
            <Clock size={19} /> Website Monitoring History
          </h3>

          {loading ? (
            <p>Loading website history...</p>
          ) : websiteHistory.length === 0 ? (
            <p>No website history available.</p>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Website</th>
                    <th>Status</th>
                    <th>HTTP Code</th>
                    <th>Response Time</th>
                    <th>Error</th>
                    <th>Checked At</th>
                  </tr>
                </thead>

                <tbody>
                  {websiteHistory.slice(0, 15).map((item) => (
                    <tr key={item.id}>
                      <td>{item.website_name}</td>

                      <td>
                        <span
                          className={getWebsiteStatusClass(item.status)}
                        >
                          {item.status}
                        </span>
                      </td>

                      <td>{item.status_code ?? "N/A"}</td>

                      <td>
                        {item.response_time_ms != null
                          ? `${item.response_time_ms} ms`
                          : "N/A"}
                      </td>

                      <td>{item.error || "None"}</td>

                      <td>{formatDate(item.checked_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* SECURITY OVERVIEW */}
        <section className="panel">
          <h3>
            <ShieldAlert size={19} /> Security Monitoring Overview
          </h3>

          <section className="stats-grid">
            {securityStats.map((item) => {
              const Icon = item.icon;

              return (
                <div className="stat-card" key={item.title}>
                  <div className={`stat-icon ${item.color}`}>
                    <Icon size={23} />
                  </div>

                  <div>
                    <p>{item.title}</p>
                    <h2>{item.value}</h2>
                  </div>
                </div>
              );
            })}
          </section>
        </section>

        {/* SECURITY ALERT HISTORY */}
        <section className="panel incident-panel">
          <h3>
            <ShieldAlert size={19} /> Recent Security Alerts
          </h3>

          {loading ? (
            <p>Loading security alerts...</p>
          ) : securityAlerts.length === 0 ? (
            <p>No security alerts detected.</p>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Alert Type</th>
                    <th>Severity</th>
                    <th>Source</th>
                    <th>Evidence</th>
                    <th>Email</th>
                    <th>Detected At</th>
                  </tr>
                </thead>

                <tbody>
                  {securityAlerts.slice(0, 15).map((alert) => (
                    <tr key={alert.id}>
                      <td>{alert.alert_type}</td>

                      <td>
                        <span className={getSeverityClass(alert.severity)}>
                          {alert.severity}
                        </span>
                      </td>

                      <td>{alert.source || "Unknown"}</td>

                      <td title={alert.evidence || ""}>
                        {(alert.evidence || "No evidence").slice(0, 65)}
                        {(alert.evidence || "").length > 65 ? "..." : ""}
                      </td>

                      <td>
                        {alert.email_sent === 1 ? (
                          <span className="online-label">SENT</span>
                        ) : (
                          <span className="offline-label">NOT SENT</span>
                        )}
                      </td>

                      <td>{formatDate(alert.timestamp)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* INCIDENT HISTORY */}
        <section className="panel incident-panel">
          <h3>Recent Incidents</h3>

          {loading ? (
            <p>Loading incidents...</p>
          ) : incidents.length === 0 ? (
            <p>No incidents found.</p>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Incident</th>
                    <th>Severity</th>
                    <th>Status</th>
                    <th>Created</th>
                  </tr>
                </thead>

                <tbody>
                  {incidents.slice(0, 10).map((incident) => (
                    <tr key={incident.id}>
                      <td>{incident.incident_type}</td>

                      <td>
                        <span className={getSeverityClass(incident.severity)}>
                          {incident.severity}
                        </span>
                      </td>

                      <td>
                        <span
                          className={
                            incident.status === "OPEN"
                              ? "open"
                              : "resolved"
                          }
                        >
                          {incident.status}
                        </span>
                      </td>

                      <td>{formatDate(incident.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* GEMINI INVESTIGATIONS */}
        <section className="panel incident-panel">
          <h3>
            <Brain size={18} /> Gemini AI Investigations
          </h3>

          {loading ? (
            <p>Loading AI reports...</p>
          ) : investigations.length === 0 ? (
            <p>No AI investigation reports available.</p>
          ) : (
            investigations.map((report) => (
              <div className="investigation-card" key={report.id}>
                <div className="investigation-heading">
                  <strong>{report.incident_type}</strong>
                  <span className="online-label">{report.status}</span>
                </div>

                <p>Incident ID: {report.incident_id}</p>
                <p>Severity: {report.severity}</p>
                <p>Created: {formatDate(report.created_at)}</p>

                <details>
                  <summary>View Gemini Analysis</summary>
                  <pre>{report.ai_analysis}</pre>
                </details>
              </div>
            ))
          )}
        </section>

        <footer>
          SentinelAI © 2026 | AI-Powered Production Reliability

          <button className="refresh-button" onClick={loadDashboard}>
            <RefreshCw size={14} /> Refresh
          </button>
        </footer>
      </main>
    </div>
  );
}

export default Dashboard;
