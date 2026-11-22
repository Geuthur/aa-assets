// React
import { useCallback, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";

// Third Party
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BaseSectionHeader, ErrorPage, queryKeys } from "aa-geuthur-react";
import { ArrowLeft } from "lucide-react";
import { Alert, Card } from "react-bootstrap";
import { useTranslation } from "react-i18next";

// AA Assets
import { assetsQueryKeys, loadAssets } from "@/Api/calls/assets";
import { createOrder, requestQueryKeys } from "@/Api/calls/requests";
import type { AssetSchema, OrderItemRequest } from "@/Api/schema";
import { AssetsTable } from "@/Components/Assets/AssetsTable";
import { OrderFloatingBar } from "@/Components/Assets/OrderFloatingBar";
import { type CartItem, OrderModal } from "@/Components/Assets/OrderModal";
import { ProjectName } from "@/constants";

/** The assets of one location; assets go into an order cart and are ordered together. */
export const LocationPage = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { locationId } = useParams();
  const [searchParams] = useSearchParams();
  const initialFlag = searchParams.get("flag") ?? undefined;
  const id = Number(locationId);
  const validId = Number.isInteger(id) && id > 0;
  // asset_pk -> amount; the assets themselves come from the loaded list so name and quantity stay current
  const [cart, setCart] = useState<ReadonlyMap<number, number>>(new Map());
  const [showOrder, setShowOrder] = useState(false);

  const { data, isLoading, isFetching, isError, error } = useQuery({
    queryKey: assetsQueryKeys.assets(id),
    queryFn: () => loadAssets(id),
    enabled: validId,
  });

  const orderMutation = useMutation({
    mutationFn: (items: OrderItemRequest[]) => createOrder(items),
    onSettled: () => {
      // A partial order is stored even when the API answers 409, so the cart is emptied either way
      // and the reloaded assets show the remaining quantities
      setShowOrder(false);
      setCart(new Map());
      queryClient.invalidateQueries({ queryKey: assetsQueryKeys.assets(id) });
      queryClient.invalidateQueries({ queryKey: requestQueryKeys.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.Menu });
    },
  });

  const assets = useMemo(() => data?.assets ?? [], [data]);

  const cartItems = useMemo<CartItem[]>(
    () =>
      assets
        .filter((asset) => cart.has(asset.asset_pk))
        .map((asset) => ({ asset, amount: Math.min(cart.get(asset.asset_pk) ?? 0, asset.quantity) })),
    [assets, cart],
  );
  const selectedIds = useMemo(() => new Set(cartItems.map((item) => item.asset.asset_pk)), [cartItems]);

  const setCartEntry = useCallback((assetPk: number, amount: number | null) => {
    setCart((current) => {
      const next = new Map(current);
      if (amount === null) {
        next.delete(assetPk);
      } else {
        next.set(assetPk, amount);
      }
      return next;
    });
  }, []);

  // A new asset starts with its whole quantity, mostly moon materials are ordered completely
  const handleToggleSelect = useCallback(
    (asset: AssetSchema) => setCartEntry(asset.asset_pk, selectedIds.has(asset.asset_pk) ? null : asset.quantity),
    [selectedIds, setCartEntry],
  );

  const openOrder = () => {
    orderMutation.reset();
    setShowOrder(true);
  };

  const submitOrder = () => {
    const items: OrderItemRequest[] = cartItems
      .filter((item) => item.amount > 0)
      .map((item) => ({ asset_pk: item.asset.asset_pk, amount: item.amount }));
    orderMutation.mutate(items);
  };

  if (!validId) {
    return <ErrorPage />;
  }

  const locationName = assets[0]?.location ?? String(id);

  return (
    // Room below the table so the floating cart bar does not cover the pagination
    <Card className={`border-0 bg-transparent ${cartItems.length > 0 ? "pb-5 mb-4" : ""}`}>
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
        selectedIds={selectedIds}
        onToggleSelect={handleToggleSelect}
        initialFlag={initialFlag}
      />

      <OrderFloatingBar itemCount={cartItems.length} onReview={openOrder} onClear={() => setCart(new Map())} />

      <OrderModal
        items={cartItems}
        show={showOrder}
        onHide={() => setShowOrder(false)}
        onUpdateAmount={(assetPk, amount) => setCartEntry(assetPk, amount)}
        onRemove={(assetPk) => setCartEntry(assetPk, null)}
        onSubmit={submitOrder}
        isPending={orderMutation.isPending}
      />
    </Card>
  );
};

export default LocationPage;
