
const API_BASE_URL = "http://127.0.0.1:8001";

async function apiRequest(endpoint) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "GET",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-cache",
      Pragma: "no-cache",
    },
  });

  if (!response.ok) {
    throw new Error(`API Error: ${endpoint} (${response.status})`);
  }

  return response.json();
}

// Production Monitoring
export const getHeartbeat = () =>
  apiRequest("/api/heartbeat/latest");

export const getAgentStatus = () =>
  apiRequest("/api/heartbeat/status");

// Incident Management
export const getIncidents = () =>
  apiRequest("/api/incidents");

// Gemini AI Investigations
export const getInvestigations = () =>
  apiRequest("/api/investigations");

// Security Monitoring
export const getSecurityAlerts = () =>
  apiRequest("/api/security/alerts");

export const getSecuritySummary = () =>
  apiRequest("/api/security/alerts/summary");

// Website Monitoring
export const getWebsites = () =>
  apiRequest("/api/websites");

export const getWebsiteHistory = () =>
  apiRequest("/api/websites/history");

// Remote Agent Monitoring
export const getRemoteAgentEvents = () =>
  apiRequest("/api/remote-agent/events");

export const getRemoteServers = () =>
  apiRequest("/api/remote-agent/servers");
