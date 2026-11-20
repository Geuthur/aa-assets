// Third Party
import { beforeEach, describe, expect, it, vi } from "vitest";

// AA Assets
import { request } from "@/__tests__/testdata";
import { apiClient } from "@/Api/Api";
import { queueAdminTasks } from "@/Api/calls/admin";
import {
  changeRequestStatus,
  createOrder,
  loadMyRequests,
  loadRequest,
  loadRequests,
  requestQueryKeys,
} from "@/Api/calls/requests";
import { ProjectName } from "@/constants";

const ok = (data: unknown) => ({ data, error: undefined, response: new Response() }) as never;
const failed = (error: unknown) => ({ data: undefined, error, response: new Response() }) as never;
const action = { success: true, message: "Done" };
const tasks = {
  force_refresh: false,
  clear_etags: false,
  update_assets: true,
  update_locations: false,
  update_parent_locations: false,
};

describe("Request API calls", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("should build the query keys below one prefix", () => {
    // Test Action & Expected Result
    expect(requestQueryKeys.manage.slice(0, 1)).toEqual(requestQueryKeys.all);
    expect(requestQueryKeys.mine.slice(0, 1)).toEqual(requestQueryKeys.all);
    expect(requestQueryKeys.detail(7)).toEqual(["Requests", "detail", 7]);
  });

  it("should load all and the own orders", async () => {
    // Test Data
    vi.spyOn(apiClient, "GET").mockResolvedValue(ok([request]));

    // Test Action
    const all = await loadRequests();
    const mine = await loadMyRequests();

    // Expected Result
    expect(all).toEqual([request]);
    expect(mine).toEqual([request]);
    expect(apiClient.GET).toHaveBeenCalledWith(`/${ProjectName}/api/requests/`);
    expect(apiClient.GET).toHaveBeenCalledWith(`/${ProjectName}/api/requests/myrequests/`);
  });

  it("should load one order", async () => {
    // Test Data
    vi.spyOn(apiClient, "GET").mockResolvedValueOnce(ok({ id: 7 }));

    // Test Action
    await loadRequest(7);

    // Expected Result
    expect(apiClient.GET).toHaveBeenCalledWith(`/${ProjectName}/api/requests/{request_id}/`, {
      params: { path: { request_id: 7 } },
    });
  });

  it("should create an order", async () => {
    // Test Data
    vi.spyOn(apiClient, "POST").mockResolvedValueOnce(ok(action));

    // Test Action
    const result = await createOrder([{ asset_pk: 11, amount: 2 }]);

    // Expected Result
    expect(result).toEqual(action);
    expect(apiClient.POST).toHaveBeenCalledWith(`/${ProjectName}/api/orders/`, {
      body: { items: [{ asset_pk: 11, amount: 2 }] },
    });
  });

  it.each([
    ["cancel", "cancel"],
    ["complete", "complete"],
    ["reopen", "reopen"],
  ] as const)("should post the status change %s", async (name, path) => {
    // Test Data
    vi.spyOn(apiClient, "POST").mockResolvedValueOnce(ok(action));

    // Test Action
    await changeRequestStatus(7, name);

    // Expected Result
    expect(apiClient.POST).toHaveBeenCalledWith(`/${ProjectName}/api/requests/{request_id}/${path}/`, {
      params: { path: { request_id: 7 } },
    });
  });

  it("should queue the admin tasks", async () => {
    // Test Data
    vi.spyOn(apiClient, "POST").mockResolvedValueOnce(ok(action));

    // Test Action
    await queueAdminTasks(tasks);

    // Expected Result
    expect(apiClient.POST).toHaveBeenCalledWith(`/${ProjectName}/api/admin/tasks/`, {
      body: tasks,
    });
  });

  it("should throw the message of the API when a request fails", async () => {
    // Test Data
    vi.spyOn(apiClient, "GET").mockResolvedValue(failed({ error: "Permission Denied" }));
    vi.spyOn(apiClient, "POST").mockResolvedValue(failed({ error: "Too fast" }));

    // Test Action & Expected Result
    await expect(loadRequests()).rejects.toThrow("Permission Denied");
    await expect(loadMyRequests()).rejects.toThrow("Permission Denied");
    await expect(loadRequest(7)).rejects.toThrow("Permission Denied");
    await expect(createOrder([{ asset_pk: 1, amount: 1 }])).rejects.toThrow("Too fast");
    await expect(changeRequestStatus(7, "cancel")).rejects.toThrow("Too fast");
    await expect(queueAdminTasks(tasks)).rejects.toThrow("Too fast");
  });
});
