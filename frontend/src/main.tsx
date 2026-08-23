import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ApiError } from "./lib/api";
import App from "./App";
import "./styles/app.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      // The backend answers 503 while its first enrichment run completes, which
      // can take minutes with an LLM configured. That is a wait, not a failure —
      // keep retrying on a fixed interval so the page fills in when the run
      // lands, and give up quickly on anything else.
      retry: (failureCount, error) =>
        error instanceof ApiError && error.isWarming ? failureCount < 60 : failureCount < 1,
      retryDelay: (_attempt, error) =>
        error instanceof ApiError && error.isWarming ? 5_000 : 1_000,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
