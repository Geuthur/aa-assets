// React
import { useState } from "react";

// Third Party
import { useQuery } from "@tanstack/react-query";
import { BaseSectionHeader } from "aa-geuthur-react";
import { Card } from "react-bootstrap";
import { useTranslation } from "react-i18next";

// AA Assets
import { assetsQueryKeys, loadLocations, loadOwners } from "@/Api/calls/assets";
import { LocationTable } from "@/Components/Location/LocationTable";
import { OwnerStatusModal } from "@/Components/Owner/OwnerStatusModal";
import { OwnerTable } from "@/Components/Owner/OwnerTable";

/** Start page: the locations with assets and the owners with their update status. */
export const MainPage = () => {
  const { t } = useTranslation();
  const [statusOwnerId, setStatusOwnerId] = useState<number | null>(null);

  const locations = useQuery({ queryKey: assetsQueryKeys.locations, queryFn: loadLocations });
  const owners = useQuery({ queryKey: assetsQueryKeys.owners, queryFn: loadOwners });

  return (
    <Card className="border-0 bg-transparent">
      <BaseSectionHeader name={t("Locations")} />
      <LocationTable
        locations={locations.data ?? []}
        isLoading={locations.isLoading}
        isFetching={locations.isFetching}
        isError={locations.isError}
      />

      <div className="mt-4">
        <BaseSectionHeader name={t("Owners")} />
        <OwnerTable
          owners={owners.data ?? []}
          isLoading={owners.isLoading}
          isFetching={owners.isFetching}
          isError={owners.isError}
          onShowStatus={setStatusOwnerId}
        />
      </div>

      <OwnerStatusModal ownerId={statusOwnerId} onHide={() => setStatusOwnerId(null)} />
    </Card>
  );
};

export default MainPage;
