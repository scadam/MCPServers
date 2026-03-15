# Workday Worker Profile OAI App

This directory contains a minimal OpenAI App that renders the `tool_get_worker` response in a friendly UI. The app is published as a React/Vite single-page application and is designed to run inside an OpenAI App host that supports calling MCP tools.

## Features

- Calls the `workday` MCP server's `get_worker` tool on load.
- Parses both structured and text-only responses, always showing a worker card.
- Provides a lightweight fallback profile so the UI can be previewed without the MCP runtime.
- Uses React Query for caching/refetch and tailwind-inspired utility classes for a compact design.

## Running locally

```powershell
cd mcp_servers/resources/oai-apps/worker-profile
npm install
npm run dev
```

The Vite dev server listens on `http://localhost:5173` by default. Update `app.json` if you change the port.

To produce a static bundle, run:

```powershell
npm run build
```

The compiled assets will be emitted to `dist/`. These files can be served by any static host or packaged as an MCP resource.

## OpenAI App manifest

`app.json` advertises the UI bundle and explicitly declares that it depends on the `workday/get_worker` tool. When the manifest is registered as an MCP resource (`resource://workday/apps/worker-profile/app.json`) an OpenAI client can discover it automatically when connected to this server.

## Directory structure

```
worker-profile/
├── app.json              # OAI manifest
├── package.json          # React app dependencies
├── README.md             # This guide
├── public/               # Static assets (icons)
├── src/                  # React source code
├── tsconfig*.json        # TypeScript settings
└── vite.config.ts        # Vite build config
```

## Next steps

- Customize the card layout with your corporate branding.
- Extend `useWorkerProfile` to join data from other Workday tools.
- Deploy the built assets behind an HTTPS CDN and update `app.json` accordingly.
