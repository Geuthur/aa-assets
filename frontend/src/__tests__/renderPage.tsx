// React
import type { ReactNode } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

// Third Party
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";

// AA Assets
import { ProjectName } from "@/constants";

/** Renders a page below the project prefix with a fresh query client (no retries). */
export const renderPage = (element: ReactNode, path = "", routePath = "") => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/${ProjectName}/${path}`]}>
        <Routes>
          <Route path={`/${ProjectName}/${routePath}`} element={element} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
};
