// React
import { useCallback, useState } from "react";

// Third Party
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BaseSectionHeader, queryKeys, useUserData } from "aa-geuthur-react";
import { Alert, Card, Nav } from "react-bootstrap";
import { useTranslation } from "react-i18next";

// AA Assets
import {
  changeRequestStatus,
  loadMyRequests,
  loadRequests,
  requestQueryKeys,
  type RequestAction,
} from "@/Api/calls/requests";
import type { RequestSchema, UserData } from "@/Api/schema";
import { RequestActionModal } from "@/Components/Requests/RequestActionModal";
import { RequestDetailModal } from "@/Components/Requests/RequestDetailModal";
import { RequestTable } from "@/Components/Requests/RequestTable";

type Tab = "manage" | "mine";

/** The orders: the own ones and, for managers, every order they may handle. */
export const RequestsPage = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const userQuery = useUserData<UserData>();
  const user = userQuery.data?.user;
  const canManage = user?.can_manage_requests ?? false;
  const [selectedTab, setTab] = useState<Tab | null>(null);
  const tab: Tab = selectedTab ?? (canManage ? "manage" : "mine");
  const [viewId, setViewId] = useState<number | null>(null);
  const [pending, setPending] = useState<{ request: RequestSchema; action: RequestAction } | null>(null);

  const manage = useQuery({
    queryKey: requestQueryKeys.manage,
    queryFn: loadRequests,
    enabled: canManage && tab === "manage",
  });
  const mine = useQuery({
    queryKey: requestQueryKeys.mine,
    queryFn: loadMyRequests,
    enabled: tab === "mine",
  });

  const actionMutation = useMutation({
    mutationFn: ({ request, action }: { request: RequestSchema; action: RequestAction }) =>
      changeRequestStatus(request.id, action),
    onSuccess: () => {
      setPending(null);
      queryClient.invalidateQueries({ queryKey: requestQueryKeys.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.Menu });
    },
  });

  const handleAction = useCallback(
    (request: RequestSchema, action: RequestAction) => {
      actionMutation.reset();
      setPending({ request, action });
    },
    [actionMutation],
  );

  const current = tab === "manage" ? manage : mine;

  return (
    <Card className="border-0 bg-transparent">
      <BaseSectionHeader name={canManage ? t("Requests") : t("My Requests")} />

      {canManage && (
        <Nav variant="tabs" role="tablist" className="mb-3" activeKey={tab} onSelect={(key) => setTab(key as Tab)}>
          <Nav.Item>
            <Nav.Link eventKey="manage">{t("Requests")}</Nav.Link>
          </Nav.Item>
          <Nav.Item>
            <Nav.Link eventKey="mine">{t("My Requests")}</Nav.Link>
          </Nav.Item>
        </Nav>
      )}

      {actionMutation.isSuccess && (
        <Alert variant="success" role="status" dismissible onClose={() => actionMutation.reset()}>
          {actionMutation.data.message}
        </Alert>
      )}

      <RequestTable
        requests={current.data ?? []}
        isLoading={current.isLoading || userQuery.isLoading}
        isFetching={current.isFetching}
        isError={current.isError}
        showRequestor={tab === "manage"}
        onView={setViewId}
        onAction={handleAction}
        exportFileName={tab === "manage" ? "requests.csv" : "my-requests.csv"}
      />

      <RequestDetailModal requestId={viewId} onHide={() => setViewId(null)} />
      <RequestActionModal
        pending={pending}
        onHide={() => setPending(null)}
        onConfirm={() => pending && actionMutation.mutate(pending)}
        isPending={actionMutation.isPending}
        errorMessage={actionMutation.isError ? actionMutation.error.message : null}
      />
    </Card>
  );
};

export default RequestsPage;
