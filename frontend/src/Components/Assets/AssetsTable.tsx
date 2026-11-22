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
import { ShoppingCart } from "lucide-react";
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
  /** Called with the asset when its order button is clicked. */
  onOrder: (asset: AssetSchema) => void;
  /** Slot above the table, e.g. the button of the multi order. */
  toolbar?: React.ReactNode;
  /** Prefills the filter of the location flag column, e.g. `CorpSAG5`. */
  initialFlag?: string;
}

/** Lists the assets of a location with price and an order button per row. */
export const AssetsTable = ({
  assets,
  isLoading = false,
  isFetching = false,
  isError = false,
  onOrder,
  toolbar,
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
        cell: ({ row }) => (
          <Button
            size="sm"
            variant="primary"
            aria-label={t("Order {{name}}", { name: row.original.name })}
            onClick={() => onOrder(row.original)}
          >
            <ShoppingCart size={14} /> {t("Order")}
          </Button>
        ),
      }),
    ],
    [t, onOrder, flagLabels],
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
      toolbar={toolbar}
      initialState={initialState}
      loadingText={t("Loading assets...")}
      emptyText={t("No assets found at this location.")}
      exportFileName="assets.csv"
    />
  );
};

export default AssetsTable;
