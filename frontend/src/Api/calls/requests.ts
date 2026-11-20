// Third Party
import { apiErrorMessage } from "aa-geuthur-react";

// AA Assets
import { apiClient } from "@/Api/Api";
import type { ActionResponse, OrderItemRequest, RequestDetailSchema, RequestSchema } from "@/Api/schema";
import { ProjectName } from "@/constants";

/** The status changes of an order, as in `POST requests/{id}/<action>/`. */
export type RequestAction = "cancel" | "complete" | "reopen";

/** Query keys of orders. */
export const requestQueryKeys = {
  all: ["Requests"] as const,
  manage: ["Requests", "manage"] as const,
  mine: ["Requests", "mine"] as const,
  detail: (requestId: number) => ["Requests", "detail", requestId] as const,
};

export async function loadRequests(): Promise<RequestSchema[]> {
  const { data, error } = await apiClient.GET(`/${ProjectName}/api/requests/`);
  if (error || !data) {
    throw new Error(apiErrorMessage(error, "Failed to load requests"));
  }
  return data;
}

export async function loadMyRequests(): Promise<RequestSchema[]> {
  const { data, error } = await apiClient.GET(`/${ProjectName}/api/requests/myrequests/`);
  if (error || !data) {
    throw new Error(apiErrorMessage(error, "Failed to load requests"));
  }
  return data;
}

export async function loadRequest(requestId: number): Promise<RequestDetailSchema> {
  const { data, error } = await apiClient.GET(`/${ProjectName}/api/requests/{request_id}/`, {
    params: { path: { request_id: requestId } },
  });
  if (error || !data) {
    throw new Error(apiErrorMessage(error, "Failed to load the order"));
  }
  return data;
}

export async function createOrder(items: OrderItemRequest[]): Promise<ActionResponse> {
  const { data, error } = await apiClient.POST(`/${ProjectName}/api/orders/`, {
    body: { items },
  });
  if (error || !data) {
    throw new Error(apiErrorMessage(error, "Failed to create the order"));
  }
  return data;
}

export async function changeRequestStatus(requestId: number, action: RequestAction): Promise<ActionResponse> {
  const params = { params: { path: { request_id: requestId } } };
  const { data, error } =
    action === "cancel"
      ? await apiClient.POST(`/${ProjectName}/api/requests/{request_id}/cancel/`, params)
      : action === "complete"
        ? await apiClient.POST(`/${ProjectName}/api/requests/{request_id}/complete/`, params)
        : await apiClient.POST(`/${ProjectName}/api/requests/{request_id}/reopen/`, params);
  if (error || !data) {
    throw new Error(apiErrorMessage(error, "Failed to change the order"));
  }
  return data;
}
