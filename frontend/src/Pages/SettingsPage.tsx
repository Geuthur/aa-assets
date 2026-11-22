// React
import React from "react";

// Third Party
import { FetchingLoader, useUserSettings } from "aa-geuthur-react";
import { BellOff, Settings2 } from "lucide-react";
import { Card } from "react-bootstrap";
import { useTranslation } from "react-i18next";

// AA Assets
import type { UserSettingsSchema, UserSettingsUpdateRequest } from "@/Api/schema";

// Styles
import styles from "@/Styles/modules/SettingsPage.module.css";

export const SettingsPage: React.FC = () => {
  const { t } = useTranslation();
  // Loads the settings and saves them optimistically (rollback on error)
  const { data, isLoading, isError, updateMutation } = useUserSettings<UserSettingsSchema, UserSettingsUpdateRequest>();

  if (isLoading) {
    return (
      <FetchingLoader message={t("Loading settings...")} />
    );
  }

  if (isError || !data) {
    return (
      <Card className={`bg-dark border-secondary ${styles["error"]}`} role="alert">
        <Card.Body className="p-0">
          {t("Failed to load settings. Please try refreshing the page.")}
        </Card.Body>
      </Card>
    );
  }

  return (
    <Card className={`bg-dark border-secondary ${styles["page"]}`}>
      <Card.Body>
        <Card.Header className={`border-0 bg-transparent p-0 ${styles["header"]}`}>
          <Settings2 size={24} aria-hidden="true" />
          <div>
            <h1 className={styles["title"]}>{t("Settings")}</h1>
            <p className={styles["description"]}>{t("Manage your Assets preferences.")}</p>
          </div>
        </Card.Header>

        <Card className="bg-body-tertiary border-0 shadow-sm mt-3">
          <Card.Body className={styles["setting-row"]}>
            <div className={styles["setting-copy"]}>
              <div className={styles["setting-title"]}>
                <BellOff size={18} aria-hidden="true" />
                <label htmlFor="disable-notifications">{t("Disable all notifications")}</label>
              </div>
              <p className={styles["setting-description"]}>
                {t("When enabled, Assets will not send notifications to your Alliance Auth or Discord account.")}
              </p>
              {updateMutation.isError && (
                <p className={styles["error-message"]} role="alert">
                  {t("Could not save this setting. Your previous preference was restored.")}
                </p>
              )}
              {updateMutation.isPending && (
                <p className={styles["save-status"]} role="status">{t("Saving...")}</p>
              )}
            </div>
            <input
              id="disable-notifications"
              className={styles["switch"]}
              type="checkbox"
              role="switch"
              checked={data.disable_notifications}
              disabled={updateMutation.isPending}
              onChange={(event) =>
                updateMutation.mutate({ disable_notifications: event.currentTarget.checked })
              }
            />
          </Card.Body>
        </Card>
      </Card.Body>
    </Card>
  );
};

export default SettingsPage;