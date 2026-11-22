// Third Party
import { renderTooltip } from "aa-geuthur-react";
import { ArrowRight, ShoppingCart, Trash2 } from "lucide-react";
import { Button } from "react-bootstrap";
import { useTranslation } from "react-i18next";

// Styles
import styles from "@/Styles/modules/OrderCart.module.css";

export interface OrderFloatingBarProps {
  /** Number of assets in the order cart; the bar is hidden at zero. */
  itemCount: number;
  onReview: () => void;
  onClear: () => void;
}

/** Floating bar at the bottom of the page that shows the order cart and opens the review. */
export const OrderFloatingBar = ({ itemCount, onReview, onClear }: OrderFloatingBarProps) => {
  const { t } = useTranslation();

  if (itemCount === 0) {
    return null;
  }

  return (
    <div className={`position-fixed bottom-0 start-50 translate-middle-x mb-4 z-3 shadow-lg ${styles["cart-floating-bar"]}`}>
      <div
        className={`text-light rounded-pill px-4 py-2 d-flex align-items-center justify-content-between gap-3 border border-light border-opacity-25 shadow ${styles["cart-bar"]}`}
      >
        <div className="d-flex align-items-center gap-2">
          <ShoppingCart size={20} />
          <span className="fw-bold">{t("Order cart: {{number}} assets", { number: itemCount })}</span>
        </div>

        <div className="d-flex align-items-center gap-2">
          {renderTooltip(
            t("Clear selection"),
            <Button
              variant="link"
              size="sm"
              aria-label={t("Clear selection")}
              className="text-light text-decoration-none p-0 opacity-75"
              onClick={onClear}
            >
              <Trash2 size={16} />
            </Button>,
          )}
          <Button
            variant="secondary"
            size="sm"
            className="rounded-pill fw-bold d-flex align-items-center gap-1 px-3"
            onClick={onReview}
          >
            <span>{t("Review Order")}</span>
            <ArrowRight size={14} />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default OrderFloatingBar;
