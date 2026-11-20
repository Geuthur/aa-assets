// Third Party
import { Badge } from "react-bootstrap";

const STATUS_VARIANTS: Record<string, string> = {
  ok: "success",
  error: "danger",
  token_error: "warning",
  incomplete: "secondary",
  in_progress: "info",
  disabled: "dark",
};

export interface OwnerStatusBadgeProps {
  /** The `update_status` value of the API, e.g. `ok` or `token_error`. */
  status: string;
  /** The translated label shown in the badge. */
  label: string;
}

/** Shows the aggregate update status of an owner as a Bootstrap badge. */
export const OwnerStatusBadge = ({ status, label }: OwnerStatusBadgeProps) => (
  <Badge bg={STATUS_VARIANTS[status] ?? "secondary"} data-testid="owner-status-badge" data-status={status}>
    {label}
  </Badge>
);

export default OwnerStatusBadge;
