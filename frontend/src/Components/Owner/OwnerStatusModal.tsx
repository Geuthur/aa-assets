// Third Party
import { useQuery } from "@tanstack/react-query";
import { BaseModal, ErrorLoader, FetchingLoader, formatDate } from "aa-geuthur-react";
import { Table } from "react-bootstrap";
import { useTranslation } from "react-i18next";

// AA Assets
import { assetsQueryKeys, loadOwner } from "@/Api/calls/assets";
import { OwnerStatusBadge } from "@/Components/Owner/OwnerStatusBadge";

export interface OwnerStatusModalProps {
  /** The owner whose status is shown; `null` hides the modal. */
  ownerId: number | null;
  onHide: () => void;
}

/** Shows the update status of every section of one owner. */
export const OwnerStatusModal = ({ ownerId, onHide }: OwnerStatusModalProps) => {
  const { t } = useTranslation();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: assetsQueryKeys.owner(ownerId ?? 0),
    queryFn: () => loadOwner(ownerId as number),
    enabled: ownerId !== null,
  });

  return (
    <BaseModal show={ownerId !== null} onHide={onHide} title={data?.name ?? t("Update status")} size="lg" centered>
      {isLoading && <FetchingLoader message={t("Loading status...")} />}
      {isError && <ErrorLoader title={t("Error")} message={error.message} />}
      {data && (
        <>
          <div className="mb-3">
            <OwnerStatusBadge status={data.update_status} label={data.update_status_label} />
          </div>
          {data.sections.length === 0 ? (
            <p className="mb-0">{t("No update has run yet.")}</p>
          ) : (
            <Table size="sm" responsive className="mb-0">
              <thead>
                <tr>
                  <th>{t("Section")}</th>
                  <th>{t("Result")}</th>
                  <th>{t("Last Run")}</th>
                  <th>{t("Last Update")}</th>
                </tr>
              </thead>
              <tbody>
                {data.sections.map((section) => (
                  <tr key={section.section}>
                    <td>{section.section_label}</td>
                    <td>
                      {section.is_success === null || section.is_success === undefined
                        ? "-"
                        : section.is_success
                          ? t("OK")
                          : section.has_token_error
                            ? t("Token Error")
                            : t("Error")}
                      {section.error_message && <div className="small text-danger">{section.error_message}</div>}
                    </td>
                    <td>{section.last_run_finished_at ? formatDate(section.last_run_finished_at) : "-"}</td>
                    <td>{section.last_update_finished_at ? formatDate(section.last_update_finished_at) : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </>
      )}
    </BaseModal>
  );
};

export default OwnerStatusModal;
