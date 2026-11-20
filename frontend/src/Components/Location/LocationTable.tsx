// React
import { useMemo } from "react";
import { Link } from "react-router-dom";

// Third Party
import { BaseTable, createBaseColumnHelper } from "aa-geuthur-react";
import { useTranslation } from "react-i18next";

// AA Assets
import type { LocationSchema } from "@/Api/schema";

const columnHelper = createBaseColumnHelper<LocationSchema>();

export interface LocationTableProps {
  locations: LocationSchema[];
  isLoading?: boolean;
  isFetching?: boolean;
  isError?: boolean;
}

/** Lists the locations that hold assets the user may see, each with a link to its assets. */
export const LocationTable = ({ locations, isLoading = false, isFetching = false, isError = false }: LocationTableProps) => {
  const { t } = useTranslation();

  const columns = useMemo(
    () => [
      columnHelper.accessor((row) => row.name ?? String(row.location_id), {
        id: "name",
        header: t("Location"),
        cell: ({ row }) => (
          <Link className="link" to={`location/${row.original.location_id}/`}>
            {row.original.name ?? row.original.location_id}
          </Link>
        ),
      }),
      columnHelper.accessor((row) => row.solar_system ?? "", {
        id: "solar_system",
        header: t("System"),
        cell: ({ getValue }) => getValue() || "-",
      }),
      columnHelper.display({
        id: "actions",
        header: t("Actions"),
        meta: { align: "right" },
        cell: ({ row }) => (
          <Link className="btn btn-sm btn-primary" to={`location/${row.original.location_id}/`}>
            {t("View Assets")}
          </Link>
        ),
      }),
    ],
    [t],
  );

  return (
    <BaseTable
      columns={columns}
      data={locations}
      isLoading={isLoading}
      isFetching={isFetching}
      isError={isError}
      loadingText={t("Loading locations...")}
      emptyText={t("No locations with assets found.")}
      exportFileName="locations.csv"
    />
  );
};

export default LocationTable;
