// React
import React from "react"
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"

// Third Party
import { QueryClientProvider } from "@tanstack/react-query";
import { AaReactProvider, AuthBase, createQueryClient, ErrorPage } from "aa-geuthur-react";
import { NuqsAdapter } from "nuqs/adapters/react-router/v8";

import { AppName, ProjectName } from "@/constants";
import AdminPage from "@/Pages/AdminPage";
import LocationPage from "@/Pages/LocationPage";
import MainPage from "@/Pages/MainPage";
import RequestsPage from "@/Pages/RequestsPage";
import SettingsPage from "@/Pages/SettingsPage";

const queryClient = createQueryClient();

function Routing() {
  return (
    <React.StrictMode>
      <AaReactProvider projectName={ProjectName} appName={AppName}>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <NuqsAdapter>
            <Routes>
              <Route path={`/${ProjectName}/`} element={<AuthBase fluidOnSmallScreens />}>
                <Route index element={<MainPage />} />
                <Route path="location/:locationId/" element={<LocationPage />} />
                <Route path="requests/" element={<RequestsPage />} />
                <Route path="admin/" element={<AdminPage />} />
                <Route path="settings/" element={<SettingsPage />} />
                <Route path="*" element={<ErrorPage />} />
              </Route>
              <Route path="*" element={<Navigate to={`/${ProjectName}/`} replace />} />
            </Routes>
          </NuqsAdapter>
        </BrowserRouter>
      </QueryClientProvider>
      </AaReactProvider>
    </React.StrictMode>
  )
}

export default Routing
