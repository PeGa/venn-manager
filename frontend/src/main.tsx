/** Application entry point. Renders the root App component. */
import { render } from "preact";
import { QueryClient, QueryClientProvider } from "@tanstack/preact-query";
import { App } from "./components/App.tsx";
import "./styles/global.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 3,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});

render(
  <QueryClientProvider client={queryClient}>
    <App />
  </QueryClientProvider>,
  document.getElementById("app")!
);
