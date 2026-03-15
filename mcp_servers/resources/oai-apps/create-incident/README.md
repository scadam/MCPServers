# ServiceNow Create Incident — OAI App

This directory contains an OpenAI App that renders a ServiceNow-style incident creation form.  The app calls the `servicenow/create_incident` MCP tool to submit the incident.

## How it works

1. An LLM-powered client determines an incident needs to be created from the conversation.
2. It opens this app (optionally passing pre-populated field values via URL query params).
3. The form shows **self-service fields** by default — short description, description, category, subcategory, urgency, caller, and comments.
4. A collapsible **Service Desk** section expands the form with impact, channel, assignment group, assigned-to, service, service offering, and configuration item.
5. On submit, the app calls `window.ai.tools.call()` → `servicenow/create_incident` MCP tool → ServiceNow Table API.
6. A success card shows the created incident number with a link back to ServiceNow.

## Pre-populating fields

The host can open the app with query-string parameters matching any `IncidentFormData` key:

```
http://localhost:5174/?short_description=Cannot+login&category=software&urgency=2
```

## Running locally

```powershell
cd mcp_servers/resources/oai-apps/create-incident
npm install
npm run dev
```

The Vite dev server listens on `http://localhost:5174`.  Update `app.json` if you change the port.

> **Note:** The `window.ai.tools.call()` bridge is only available inside an OpenAI App host.  Outside the host the form will render but submission will show an error.
