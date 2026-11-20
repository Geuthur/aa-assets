// React
import { useMemo } from "react";

// Third Party
import { BaseTable, createBaseColumnHelper, formatDate } from "aa-geuthur-react";
import { Check, Eye, RotateCcw, X } from "lucide-react";
import { Button } from "react-bootstrap";
import { useTranslation } from "react-i18next";

// AA Assets
import type { RequestAction } from "@/Api/calls/requests";
import type { RequestSchema } from "@/Api/schema";
import { RequestStatusBadge } from "@/Components/Requests/RequestStatusBadge";

const columnHelper = createBaseColumnHelper<RequestSchema>();

export interface RequestTableProps {
  requests: RequestSchema[];
  isLoading?: boolean;
  isFetching?: boolean;
  isError?: boolean;
  /** Show the column with the user who ordered (lists of all orders). */
  showRequestor?: boolean;
  /** Called with the order id when its items are to be shown. */
  onView: (requestId: number) => void;
  /** Called with the order and the chosen status change. */
  onAction: (request: RequestSchema, action: RequestAction) => void;
  /** Name of the CSV export. */
  exportFileName?: string;
}

/** Lists orders with status, dates and the buttons for the status changes the user may do. */
export const RequestTable = ({
  requests,
  isLoading = false,
  isFetching = false,
  isError = false,
  showRequestor = false,
  onView,
  onAction,
  exportFileName = "requests.csv",
}: RequestTableProps) => {
  const { t } = useTranslation();

  const columns = useMemo(
    () => [
      columnHelper.accessor("id", {
        header: t("ID"),
        enableColumnFilter: false,
      }),
      ...(showRequestor
        ? [
            columnHelper.accessor((row) => String(row.requestor ?? ""), {
              id: "requestor",
              header: t("Requestor"),
            }),
          ]
        : []),
      columnHelper.accessor("status", {
        header: t("Status"),
        cell: ({ row }) => <RequestStatusBadge status={row.original.action} label={row.original.status} />,
      }),
      columnHelper.accessor("created", {
        header: t("Created"),
        enableColumnFilter: false,
        cell: ({ getValue }) => formatDate(getValue()),
      }),
      columnHelper.accessor((row) => (row.approver ? String(row.approver) : ""), {
        id: "approver",
        header: t("Handled by"),
        cell: ({ getValue }) => getValue() || "-",
      }),
      columnHelper.display({
        id: "actions",
        header: t("Actions"),
        meta: { align: "right" },
        cell: ({ row }) => {
          const request = row.original;
          return (
            <div className="d-inline-flex gap-1">
              <Button
                size="sm"
                variant="outline-light"
                title={t("Show order")}
                aria-label={t("Show order {{id}}", { id: request.id })}
                onClick={() => onView(request.id)}
              >
                <Eye size={14} />
              </Button>
              {request.can_complete && (
                <Button
                  size="sm"
                  variant="success"
                  title={t("Complete")}
                  aria-label={t("Complete order {{id}}", { id: request.id })}
                  onClick={() => onAction(request, "complete")}
                >
                  <Check size={14} />
                </Button>
              )}
              {request.can_cancel && (
                <Button
                  size="sm"
                  variant="danger"
                  title={t("Cancel")}
                  aria-label={t("Cancel order {{id}}", { id: request.id })}
                  onClick={() => onAction(request, "cancel")}
                >
                  <X size={14} />
                </Button>
              )}
              {request.can_reopen && (
                <Button
                  size="sm"
                  variant="warning"
                  title={t("Reopen")}
                  aria-label={t("Reopen order {{id}}", { id: request.id })}
                  onClick={() => onAction(request, "reopen")}
                >
                  <RotateCcw size={14} />
                </Button>
              )}
            </div>
          );
        },
      }),
    ],
    [t, showRequestor, onView, onAction],
  );

  return (
    <BaseTable
      columns={columns}
      data={requests}
      isLoading={isLoading}
      isFetching={isFetching}
      isError={isError}
      initialState={{ sorting: [{ id: "created", desc: true }] }}
      loadingText={t("Loading orders...")}
      emptyText={t("No orders found.")}
      exportFileName={exportFileName}
    />
  );
};

export default RequestTable;
