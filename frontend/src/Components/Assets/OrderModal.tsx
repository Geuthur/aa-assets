// Third Party
import { BaseModal, formatNumber, itemImageUrl, renderTooltip } from "aa-geuthur-react";
import { Send, ShoppingCart, Trash2 } from "lucide-react";
import { Button, Form, Spinner, Table } from "react-bootstrap";
import { useTranslation } from "react-i18next";

// AA Assets
import type { AssetSchema } from "@/Api/schema";

/** One asset in the order cart with the amount to order. */
export interface CartItem {
  asset: AssetSchema;
  amount: number;
}

export interface OrderModalProps {
  items: CartItem[];
  show: boolean;
  onHide: () => void;
  /** Called with the new amount, already limited to 0 up to the available quantity. */
  onUpdateAmount: (assetPk: number, amount: number) => void;
  onRemove: (assetPk: number) => void;
  onSubmit: () => void;
  isPending?: boolean;
}

/** Review of the order cart: one amount field per asset, limited to the available quantity. */
export const OrderModal = ({
  items,
  show,
  onHide,
  onUpdateAmount,
  onRemove,
  onSubmit,
  isPending = false,
}: OrderModalProps) => {
  const { t } = useTranslation();

  const setAmount = (asset: AssetSchema, value: string) => {
    const parsed = parseInt(value, 10);
    // An empty field is 0 so the amount can be retyped; items below 1 are not ordered
    const amount = Number.isNaN(parsed) ? 0 : Math.min(Math.max(parsed, 0), asset.quantity);
    onUpdateAmount(asset.asset_pk, amount);
  };

  return (
    <BaseModal
      show={show}
      onHide={onHide}
      size="lg"
      scrollable
      title={
        <div className="d-flex align-items-center gap-2">
          <ShoppingCart size={20} />
          <span>{t("Review Order")}</span>
        </div>
      }
      footer={
        <>
          <Button variant="secondary" onClick={onHide} disabled={isPending}>
            {t("Cancel")}
          </Button>
          <Button
            variant="success"
            className="d-flex align-items-center gap-2"
            onClick={onSubmit}
            disabled={!items.some((item) => item.amount > 0) || isPending}
          >
            {isPending ? <Spinner size="sm" animation="border" /> : <Send size={16} />}
            {t("Place Order")}
          </Button>
        </>
      }
    >
      <Table size="sm" responsive className="mb-0 align-middle">
        <thead>
          <tr>
            <th>{t("Name")}</th>
            <th>{t("Location Flag")}</th>
            <th className="text-end">{t("Available")}</th>
            <th className="text-end">{t("Amount")}</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {items.length === 0 ? (
            <tr>
              <td colSpan={5} className="text-center py-4">
                {t("Your order cart is empty.")}
              </td>
            </tr>
          ) : (
            items.map(({ asset, amount }) => (
              <tr key={asset.asset_pk}>
                <td>
                  <div className="d-flex align-items-center gap-2">
                    <img src={itemImageUrl(asset.type_id, 32)} alt="" width={32} height={32} />
                    <span>{asset.name}</span>
                  </div>
                </td>
                <td>{asset.location_flag}</td>
                <td className="text-end">{formatNumber(asset.quantity)}</td>
                <td className="text-end">
                  <Form.Control
                    type="number"
                    size="sm"
                    min={1}
                    max={asset.quantity}
                    className="w-auto ms-auto"
                    aria-label={t("Amount of {{name}}", { name: asset.name })}
                    value={amount || ""}
                    onChange={(event) => setAmount(asset, event.currentTarget.value)}
                  />
                </td>
                <td className="text-end">
                  {renderTooltip(
                    t("Remove item"),
                    <Button
                      variant="danger"
                      size="sm"
                      className="p-1"
                      aria-label={t("Remove {{name}} from order", { name: asset.name })}
                      onClick={() => onRemove(asset.asset_pk)}
                    >
                      <Trash2 size={15} />
                    </Button>,
                  )}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </Table>
    </BaseModal>
  );
};

export default OrderModal;
