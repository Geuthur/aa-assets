// React
import { useMemo } from "react";

// Third Party
import {
  BaseTable,
  characterImageUrl,
  corporationImageUrl,
  createBaseColumnHelper,
  formatRelativeTime,
} from "aa-geuthur-react";
import { Info } from "lucide-react";
import { Button } from "react-bootstrap";
import { useTranslation } from "react-i18next";

// AA Assets
import type { OwnerSchema } from "@/Api/schema";
import { OwnerStatusBadge } from "@/Components/Owner/OwnerStatusBadge";

const columnHelper = createBaseColumnHelper<OwnerSchema>();

export interface OwnerTableProps {
  owners: OwnerSchema[];
  isLoading?: boolean;
  isFetching?: boolean;
  isError?: boolean;
  /** Called with the owner id when the status button of a row is clicked. */
  onShowStatus: (ownerId: number) => void;
}

/** Lists the owners (characters and corporations) with their update status. */
export const OwnerTable = ({
  owners,
  isLoading = false,
  isFetching = false,
  isError = false,
  onShowStatus,
}: OwnerTableProps) => {
  const { t } = useTranslation();

  const columns = useMemo(
    () => [
      columnHelper.accessor("name", {
        header: t("Owner"),
        cell: ({ row }) => {
          const owner = row.original;
          const image =
            owner.owner_type === "corporation" && owner.corporation_id
              ? corporationImageUrl(owner.corporation_id, 32)
              : owner.character_id
                ? characterImageUrl(owner.character_id, 32)
                : null;
          return (
            <div className="d-flex align-items-center gap-2">
              {image && <img src={image} alt="" className="rounded" width={32} height={32} />}
              <span>{owner.name}</span>
            </div>
          );
        },
      }),
      columnHelper.accessor("owner_type", {
        header: t("Type"),
        cell: ({ getValue }) => (getValue() === "corporation" ? t("Corporation") : t("Character")),
      }),
      columnHelper.accessor("update_status", {
        header: t("Status"),
        cell: ({ row }) => (
          <OwnerStatusBadge status={row.original.update_status} label={row.original.update_status_label} />
        ),
      }),
      columnHelper.accessor("last_update", {
        header: t("Last Update"),
        enableColumnFilter: false,
        cell: ({ getValue }) => {
          const value = getValue();
          return value ? formatRelativeTime(value) : "-";
        },
      }),
      columnHelper.display({
        id: "actions",
        header: t("Actions"),
        meta: { align: "right" },
        cell: ({ row }) => (
          <Button
            size="sm"
            variant="outline-light"
            title={t("Update status")}
            aria-label={t("Update status of {{name}}", { name: row.original.name })}
            onClick={() => onShowStatus(row.original.id)}
          >
            <Info size={14} />
          </Button>
        ),
      }),
    ],
    [t, onShowStatus],
  );

  return (
    <BaseTable
      columns={columns}
      data={owners}
      isLoading={isLoading}
      isFetching={isFetching}
      isError={isError}
      loadingText={t("Loading owners...")}
      emptyText={t("No characters or corporations added yet.")}
      exportFileName="owners.csv"
    />
  );
};

export default OwnerTable;
