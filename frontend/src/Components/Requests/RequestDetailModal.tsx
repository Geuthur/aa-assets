// Third Party
import { useQuery } from "@tanstack/react-query";
import { BaseModal, ErrorLoader, FetchingLoader, formatNumber, itemImageUrl } from "aa-geuthur-react";
import { Table } from "react-bootstrap";
import { useTranslation } from "react-i18next";

// AA Assets
import { loadRequest, requestQueryKeys } from "@/Api/calls/requests";
import { RequestStatusBadge } from "@/Components/Requests/RequestStatusBadge";

export interface RequestDetailModalProps {
  /** The order that is shown; `null` hides the modal. */
  requestId: number | null;
  onHide: () => void;
}

/** Shows the items of one order. */
export const RequestDetailModal = ({ requestId, onHide }: RequestDetailModalProps) => {
  const { t } = useTranslation();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: requestQueryKeys.detail(requestId ?? 0),
    queryFn: () => loadRequest(requestId as number),
    enabled: requestId !== null,
  });

  const title = data
    ? t("Order for {{requestor}} - ID: {{id}}", { requestor: data.requestor, id: data.id })
    : t("Order");

  return (
    <BaseModal show={requestId !== null} onHide={onHide} title={title} scrollable>
      {isLoading && <FetchingLoader message={t("Loading order...")} />}
      {isError && <ErrorLoader title={t("Error")} message={error.message} />}
      {data && (
        <>
          <div className="mb-3">
            <RequestStatusBadge status={data.status} label={data.status_label} />
          </div>
          <Table size="sm" responsive className="mb-0 align-middle">
            <thead>
              <tr>
                <th>{t("Name")}</th>
                <th className="text-end">{t("Quantity")}</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <tr key={`${item.type_id}-${item.name}`}>
                  <td>
                    <div className="d-flex align-items-center gap-2">
                      <img src={itemImageUrl(item.type_id, 32)} alt="" width={32} height={32} />
                      <span>{item.name}</span>
                    </div>
                  </td>
                  <td className="text-end">{formatNumber(item.quantity)}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        </>
      )}
    </BaseModal>
  );
};

export default RequestDetailModal;
