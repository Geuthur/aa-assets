// React
import { useCallback, useState } from "react";
import { Link, useParams } from "react-router-dom";

// Third Party
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BaseSectionHeader, ErrorPage, queryKeys } from "aa-geuthur-react";
import { ArrowLeft, ShoppingBasket } from "lucide-react";
import { Alert, Button, Card } from "react-bootstrap";
import { useTranslation } from "react-i18next";

// AA Assets
import { assetsQueryKeys, loadAssets } from "@/Api/calls/assets";
import { createOrder, requestQueryKeys } from "@/Api/calls/requests";
import type { AssetSchema, OrderItemRequest } from "@/Api/schema";
import { AssetsTable } from "@/Components/Assets/AssetsTable";
import { OrderModal } from "@/Components/Assets/OrderModal";
import { ProjectName } from "@/constants";

/** The assets of one location with single and multi order. */
export const LocationPage = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { locationId } = useParams();
  const id = Number(locationId);
  const validId = Number.isInteger(id) && id > 0;
  const [orderAssets, setOrderAssets] = useState<AssetSchema[]>([]);
  const [showOrder, setShowOrder] = useState(false);

  const { data, isLoading, isFetching, isError, error } = useQuery({
    queryKey: assetsQueryKeys.assets(id),
    queryFn: () => loadAssets(id),
    enabled: validId,
  });

  const orderMutation = useMutation({
    mutationFn: (items: OrderItemRequest[]) => createOrder(items),
    onSettled: () => {
      // A partial order is stored even when the API answers 409, so the modal closes either way
      // and the reloaded assets show the remaining quantities
      setShowOrder(false);
      queryClient.invalidateQueries({ queryKey: assetsQueryKeys.assets(id) });
      queryClient.invalidateQueries({ queryKey: requestQueryKeys.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.Menu });
    },
  });

  const openOrder = useCallback(
    (assets: AssetSchema[]) => {
      orderMutation.reset();
      setOrderAssets(assets);
      setShowOrder(true);
    },
    [orderMutation],
  );
  const handleOrder = useCallback((asset: AssetSchema) => openOrder([asset]), [openOrder]);

  if (!validId) {
    return <ErrorPage />;
  }

  const assets = data?.assets ?? [];
  const locationName = assets[0]?.location ?? String(id);

  return (
    <Card className="border-0 bg-transparent">
      <BaseSectionHeader name={t("Assets in {{location}}", { location: locationName })}>
        <Link className="btn btn-sm btn-secondary" to={`/${ProjectName}/`}>
          <ArrowLeft size={14} /> {t("Locations")}
        </Link>
      </BaseSectionHeader>

      {orderMutation.isSuccess && (
        <Alert variant="success" role="status" dismissible onClose={() => orderMutation.reset()}>
          {orderMutation.data.message}
        </Alert>
      )}
      {orderMutation.isError && (
        <Alert variant="danger" role="alert" dismissible onClose={() => orderMutation.reset()}>
          {orderMutation.error.message}
        </Alert>
      )}
      {isError && (
        <Alert variant="danger" role="alert">
          {error.message}
        </Alert>
      )}

      <AssetsTable
        assets={assets}
        isLoading={isLoading}
        isFetching={isFetching}
        isError={isError}
        onOrder={handleOrder}
        toolbar={
          <Button
            size="sm"
            variant="primary"
            disabled={assets.length === 0}
            onClick={() => openOrder(assets)}
          >
            <ShoppingBasket size={14} /> {t("Multi Order")}
          </Button>
        }
      />

      <OrderModal
        assets={orderAssets}
        show={showOrder}
        onHide={() => setShowOrder(false)}
        onSubmit={(items) => orderMutation.mutate(items)}
        isPending={orderMutation.isPending}
      />
    </Card>
  );
};

export default LocationPage;
