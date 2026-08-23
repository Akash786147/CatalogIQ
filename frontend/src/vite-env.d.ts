/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL for the FastAPI backend. Empty in dev — Vite proxies /api. */
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
