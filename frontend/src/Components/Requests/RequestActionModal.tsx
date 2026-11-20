// Third Party
import { BaseModal } from "aa-geuthur-react";
import { Alert, Button } from "react-bootstrap";
import { useTranslation } from "react-i18next";

// AA Assets
import type { RequestAction } from "@/Api/calls/requests";
import type { RequestSchema } from "@/Api/schema";

export interface RequestActionModalProps {
  /** The order and the status change to confirm; `null` hides the modal. */
  pending: { request: RequestSchema; action: RequestAction } | null;
  onHide: () => void;
  onConfirm: () => void;
  isPending?: boolean;
  /** Message of a failed status change. */
  errorMessage?: string | null;
}

/** Asks before an order is cancelled, completed or reopened. */
export const RequestActionModal = ({
  pending,
  onHide,
  onConfirm,
  isPending = false,
  errorMessage,
}: RequestActionModalProps) => {
  const { t } = useTranslation();

  const texts: Record<RequestAction, { title: string; text: string; variant: string }> = {
    cancel: {
      title: t("Cancel order"),
      text: t("Are you sure you want to cancel order {{id}}?", { id: pending?.request.id }),
      variant: "danger",
    },
    complete: {
      title: t("Complete order"),
      text: t("Are you sure you want to mark order {{id}} as completed?", { id: pending?.request.id }),
      variant: "success",
    },
    reopen: {
      title: t("Reopen order"),
      text: t("Are you sure you want to reopen order {{id}}?", { id: pending?.request.id }),
      variant: "warning",
    },
  };
  const content = pending ? texts[pending.action] : null;

  return (
    <BaseModal
      show={pending !== null}
      onHide={onHide}
      title={content?.title ?? ""}
      size={undefined}
      footer={
        <>
          <Button variant="secondary" onClick={onHide} disabled={isPending}>
            {t("Close")}
          </Button>
          <Button variant={content?.variant ?? "primary"} onClick={onConfirm} disabled={isPending}>
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
      <p className="mb-0">{content?.text}</p>
    </BaseModal>
  );
};

export default RequestActionModal;
