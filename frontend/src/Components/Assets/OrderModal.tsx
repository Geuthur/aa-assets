// React
import { useState } from "react";

// Third Party
import { BaseModal, formatNumber, itemImageUrl } from "aa-geuthur-react";
import { Alert, Button, Form, Table } from "react-bootstrap";
import { useTranslation } from "react-i18next";

// AA Assets
import type { AssetSchema, OrderItemRequest } from "@/Api/schema";

export interface OrderModalProps {
  /** The assets that can be ordered; one asset is a single order, several a multi order. */
  assets: AssetSchema[];
  show: boolean;
  onHide: () => void;
  /** Called with the items that have an amount above zero. */
  onSubmit: (items: OrderItemRequest[]) => void;
  isPending?: boolean;
  /** Message of a failed order. */
  errorMessage?: string | null;
}

/** Order one or more assets: one amount field per asset, limited to the available quantity. */
export const OrderModal = ({ assets, show, onHide, onSubmit, isPending = false, errorMessage }: OrderModalProps) => {
  const { t } = useTranslation();
  const [amounts, setAmounts] = useState<Record<number, string>>({});
  const [showRequired, setShowRequired] = useState(false);
  const single = assets.length === 1;

  const setAmount = (asset: AssetSchema, value: string) => {
    const parsed = parseInt(value, 10);
    const limited = Number.isNaN(parsed) ? "" : String(Math.min(Math.max(parsed, 0), asset.quantity));
    setAmounts((current) => ({ ...current, [asset.asset_pk]: limited }));
  };

  const handleSubmit = () => {
    const items = assets
      .map((asset) => ({ asset_pk: asset.asset_pk, amount: parseInt(amounts[asset.asset_pk] ?? "", 10) }))
      .filter((item) => !Number.isNaN(item.amount) && item.amount > 0);
    if (items.length === 0) {
      setShowRequired(true);
      return;
    }
    setShowRequired(false);
    onSubmit(items);
  };

  const handleExited = () => {
    setAmounts({});
    setShowRequired(false);
  };

  const title = single ? t("Order {{name}}", { name: assets[0]?.name }) : t("Multi Order");

  return (
    <BaseModal
      show={show}
      onHide={onHide}
      onExited={handleExited}
      title={title}
      size={single ? undefined : "lg"}
      scrollable
      footer={
        <>
          <Button variant="danger" onClick={onHide} disabled={isPending}>
            {t("Cancel")}
          </Button>
          <Button variant="success" onClick={handleSubmit} disabled={isPending}>
            {t("Confirm")}
          </Button>
        </>
      }
    >
      {errorMessage && (
        <Alert variant="danger" role="alert">
          {errorMessage}
        </Alert>
      )}
      {showRequired && (
        <Alert variant="warning" role="alert">
          {t("Enter an amount of at least 1 for one asset.")}
        </Alert>
      )}
      <Table size="sm" responsive className="mb-0 align-middle">
        <thead>
          <tr>
            <th>{t("Name")}</th>
            <th className="text-end">{t("Available")}</th>
            <th className="text-end">{t("Amount")}</th>
          </tr>
        </thead>
        <tbody>
          {assets.map((asset) => (
            <tr key={asset.asset_pk}>
              <td>
                <div className="d-flex align-items-center gap-2">
                  <img src={itemImageUrl(asset.type_id, 32)} alt="" width={32} height={32} />
                  <span>{asset.name}</span>
                </div>
              </td>
              <td className="text-end">{formatNumber(asset.quantity)}</td>
              <td className="text-end">
                <div className="d-flex justify-content-end gap-2">
                  <Form.Control
                    type="number"
                    size="sm"
                    min={0}
                    max={asset.quantity}
                    className="w-auto"
                    aria-label={t("Amount of {{name}}", { name: asset.name })}
                    value={amounts[asset.asset_pk] ?? ""}
                    onChange={(event) => setAmount(asset, event.currentTarget.value)}
                  />
                  <Button size="sm" variant="secondary" onClick={() => setAmount(asset, String(asset.quantity))}>
                    {t("All")}
                  </Button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </BaseModal>
  );
};

export default OrderModal;
