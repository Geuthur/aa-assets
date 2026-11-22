// React
import { useMemo } from "react";

// Third Party
import {
  BaseTable,
  createBaseColumnHelper,
  formatIsk,
  formatNumber,
  itemImageUrl,
} from "aa-geuthur-react";
import { Check, Plus } from "lucide-react";
import { Button } from "react-bootstrap";
import { useTranslation } from "react-i18next";

// AA Assets
import type { AssetSchema } from "@/Api/schema";

const columnHelper = createBaseColumnHelper<AssetSchema>();

export interface AssetsTableProps {
  assets: AssetSchema[];
  isLoading?: boolean;
  isFetching?: boolean;
  isError?: boolean;
  /** `asset_pk` of the assets in the order cart. */
  selectedIds: ReadonlySet<number>;
  /** Called with the asset when its cart button is clicked: adds it or takes it out again. */
  onToggleSelect: (asset: AssetSchema) => void;
  /** Prefills the filter of the location flag column, e.g. `CorpSAG5`. */
  initialFlag?: string;
}

/** Lists the assets of a location with price and a button per row for the order cart. */
export const AssetsTable = ({
  assets,
  isLoading = false,
  isFetching = false,
  isError = false,
  selectedIds,
  onToggleSelect,
  initialFlag,
}: AssetsTableProps) => {
  const { t } = useTranslation();

  const flagLabels = useMemo(
    () => new Map(assets.map((asset) => [asset.location_flag_code, asset.location_flag])),
    [assets],
  );

  const columns = useMemo(
    () => [
      columnHelper.accessor("name", {
        header: t("Name"),
        cell: ({ row }) => (
          <div className="d-flex align-items-center gap-2">
            <img src={itemImageUrl(row.original.type_id, 32)} alt="" width={32} height={32} />
            <span>{row.original.name}</span>
          </div>
        ),
      }),
      columnHelper.accessor("quantity", {
        header: t("Quantity"),
        meta: { align: "right" },
        enableColumnFilter: false,
        cell: ({ getValue }) => formatNumber(getValue()),
      }),
      columnHelper.accessor((row) => row.location ?? "", {
        id: "location",
        header: t("Location"),
      }),
      columnHelper.accessor("location_flag", {
        header: t("Location Flag"),
        // The ?flag= link filters by the ESI code, the column shows its translated label
        filterFn: (row, columnId, filterValue: string) =>
          row.original.location_flag_code === filterValue ||
          String(row.getValue(columnId)).toLowerCase().includes(filterValue.toLowerCase()),
        meta: { filterOptionLabel: (value: string) => flagLabels.get(value) ?? value },
      }),
      columnHelper.accessor((row) => row.price ?? null, {
        id: "price",
        header: t("Price"),
        meta: { align: "right" },
        enableColumnFilter: false,
        cell: ({ getValue }) => {
          const value = getValue();
          return value === null ? t("N/A") : formatIsk(value);
        },
      }),
      columnHelper.display({
        id: "actions",
        header: t("Actions"),
        meta: { align: "right" },
        cell: ({ row }) => {
          const selected = selectedIds.has(row.original.asset_pk);
          return (
            <Button
              size="sm"
              variant={selected ? "success" : "primary"}
              aria-label={
                selected
                  ? t("Remove {{name}} from order", { name: row.original.name })
                  : t("Add {{name}} to order", { name: row.original.name })
              }
              aria-pressed={selected}
              onClick={() => onToggleSelect(row.original)}
            >
              {selected ? <Check size={14} /> : <Plus size={14} />} {selected ? t("Added") : t("Add")}
            </Button>
          );
        },
      }),
    ],
    [t, selectedIds, onToggleSelect, flagLabels],
  );

  const initialState = useMemo(
    () => (initialFlag ? { columnFilters: [{ id: "location_flag", value: initialFlag }] } : undefined),
    [initialFlag],
  );

  return (
    <BaseTable
      columns={columns}
      data={assets}
      isLoading={isLoading}
      isFetching={isFetching}
      isError={isError}
      initialState={initialState}
      loadingText={t("Loading assets...")}
      emptyText={t("No assets found at this location.")}
      exportFileName="assets.csv"
    />
  );
};

export default AssetsTable;
