// Third Party
import { Badge } from "react-bootstrap";

const STATUS_VARIANTS: Record<string, string> = {
  OP: "warning",
  CD: "success",
  CL: "secondary",
};

export interface RequestStatusBadgeProps {
  /** The status code of the API (`action` in the list, `status` in the detail). */
  status: string;
  /** The translated label shown in the badge. */
  label: string;
}

/** Shows the status of an order as a Bootstrap badge. */
export const RequestStatusBadge = ({ status, label }: RequestStatusBadgeProps) => (
  <Badge bg={STATUS_VARIANTS[status] ?? "secondary"} data-testid="request-status-badge" data-status={status}>
    {label}
  </Badge>
);

export default RequestStatusBadge;
