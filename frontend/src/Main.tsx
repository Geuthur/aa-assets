/* eslint-disable import-headings/import-headings -- the global index.css must load before the CSS modules */
// React
import React from 'react'
import ReactDOM from "react-dom/client";

// Third Party
import { initI18n } from "aa-geuthur-react";

// Styles
import '@/Styles/index.css';

import { AppName, ProjectName } from '@/constants';
import Routing from '@/Routing';
export { AppName, ProjectName };

// Language from Django's LANGUAGE_CODE (lang="..." on the root div), texts of the app from static/<ProjectName>/i18n
initI18n(ProjectName, `${AppName}-root`);

const container = typeof document !== "undefined" ? document.getElementById(`${AppName}-root`) : null;

if (container) {
  ReactDOM.createRoot(container).render(
    <React.StrictMode>
      <Routing />
    </React.StrictMode>,
  );
}

