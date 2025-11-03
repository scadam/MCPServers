# MCP Servers Project Workspace

This repository now hosts the Python-based MCP Servers solution, starting with the Workday
implementation located under `mcp_servers/`.

- For setup, development workflow, and deployment guidance, see `mcp_servers/README.md`.
- All legacy agent and Azure Functions assets have been removed as part of the cleanup.
- Additional MCP services (ServiceNow, Salesforce, etc.) should follow the same shared
    patterns defined in the `mcp_servers` package.
