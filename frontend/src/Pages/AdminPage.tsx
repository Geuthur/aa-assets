// React
import { useState } from "react";

// Third Party
import { useMutation } from "@tanstack/react-query";
import { BaseSectionHeader, ErrorPage, FetchingLoader, useUserData } from "aa-geuthur-react";
import { Alert, Button, Card, Form } from "react-bootstrap";
import { useTranslation } from "react-i18next";

// AA Assets
import { queueAdminTasks } from "@/Api/calls/admin";
import type { AdminTasksRequest, UserData } from "@/Api/schema";

const EMPTY_TASKS: AdminTasksRequest = {
  force_refresh: false,
  clear_etags: false,
  update_assets: false,
  update_locations: false,
  update_parent_locations: false,
};

/** Administration (superusers): queue the maintenance tasks. */
export const AdminPage = () => {
  const { t } = useTranslation();
  const userQuery = useUserData<UserData>();
  const user = userQuery.data?.user;
  const [tasks, setTasks] = useState(EMPTY_TASKS);

  const mutation = useMutation({
    mutationFn: (payload: AdminTasksRequest) => queueAdminTasks(payload),
    onSuccess: () => setTasks(EMPTY_TASKS),
  });

  if (userQuery.isLoading) {
    return <FetchingLoader message={t("Loading...")} />;
  }
  if (!user?.is_admin) {
    return <ErrorPage />;
  }

  const options: { key: keyof AdminTasksRequest; label: string }[] = [
    { key: "clear_etags", label: t("Clear all cached ETags") },
    { key: "update_assets", label: t("Update All Assets") },
    { key: "update_locations", label: t("Update All Locations") },
    { key: "update_parent_locations", label: t("Update All Parent Locations") },
  ];

  const toggle = (key: keyof AdminTasksRequest) => (event: React.ChangeEvent<HTMLInputElement>) => {
    const checked = event.currentTarget.checked;
    setTasks((current) => ({ ...current, [key]: checked }));
  };

  return (
    <Card className="border-0 bg-transparent">
      <BaseSectionHeader name={t("Administration")} />
      {mutation.isSuccess && (
        <Alert variant={mutation.data.success ? "success" : "warning"} role="status">
          {mutation.data.message}
        </Alert>
      )}
      {mutation.isError && (
        <Alert variant="danger" role="alert">
          {mutation.error.message}
        </Alert>
      )}
      <Card className="bg-dark border-secondary">
        <Card.Body>
          <Form
            onSubmit={(event) => {
              event.preventDefault();
              mutation.mutate(tasks);
            }}
          >
            <Form.Check
              id="force_refresh"
              type="checkbox"
              label={t("Mark all tasks as Force Refresh")}
              checked={tasks.force_refresh}
              onChange={toggle("force_refresh")}
            />
            <hr />
            {options.map((option) => (
              <Form.Check
                key={option.key}
                id={option.key}
                type="checkbox"
                className="mb-2"
                label={option.label}
                checked={tasks[option.key]}
                onChange={toggle(option.key)}
              />
            ))}
            <Button type="submit" variant="primary" className="mt-2" disabled={mutation.isPending}>
              {t("Submit")}
            </Button>
          </Form>
        </Card.Body>
      </Card>
    </Card>
  );
};

export default AdminPage;
