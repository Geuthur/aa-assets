// Third Party
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useUserData } from "aa-geuthur-react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// AA Assets
import { renderPage } from "@/__tests__/renderPage";
import { request } from "@/__tests__/testdata";
import * as requestsApi from "@/Api/calls/requests";
import { RequestsPage } from "@/Pages/RequestsPage";

vi.mock("aa-geuthur-react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("aa-geuthur-react")>();
  return { ...actual, useUserData: vi.fn() };
});
vi.mock("@/Api/calls/requests", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/Api/calls/requests")>();
  return {
    ...actual,
    loadRequests: vi.fn(),
    loadMyRequests: vi.fn(),
    loadRequest: vi.fn(),
    changeRequestStatus: vi.fn(),
  };
});

const mockUser = (canManage: boolean) =>
  vi.mocked(useUserData).mockReturnValue({
    data: { user: { can_manage_requests: canManage, is_admin: false } },
    isLoading: false,
  } as unknown as ReturnType<typeof useUserData>);

describe("RequestsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(requestsApi.loadRequests).mockResolvedValue([request]);
    vi.mocked(requestsApi.loadMyRequests).mockResolvedValue([{ ...request, id: 8, can_complete: false }]);
  });

  it("should show only the own orders without the right to manage", async () => {
    // Test Data
    mockUser(false);

    // Test Action
    renderPage(<RequestsPage />, "requests/", "requests/");

    // Expected Result
    expect(await screen.findByRole("button", { name: "Show order 8" })).toBeInTheDocument();
    expect(screen.queryByRole("tab")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Complete order 8" })).not.toBeInTheDocument();
    expect(requestsApi.loadRequests).not.toHaveBeenCalled();
  });

  it("should show all orders and the own ones in tabs for managers", async () => {
    // Test Data
    const user = userEvent.setup();
    mockUser(true);

    // Test Action
    renderPage(<RequestsPage />, "requests/", "requests/");

    // Expected Result
    expect(await screen.findByText("alice")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "My Requests" }));
    expect(await screen.findByRole("button", { name: "Show order 8" })).toBeInTheDocument();
  });

  it("should complete an order after the confirmation", async () => {
    // Test Data
    const user = userEvent.setup();
    mockUser(true);
    vi.mocked(requestsApi.changeRequestStatus).mockResolvedValue({ success: true, message: "Request completed" });

    // Test Action
    renderPage(<RequestsPage />, "requests/", "requests/");
    await user.click(await screen.findByRole("button", { name: "Complete order 7" }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Confirm" }));

    // Expected Result
    expect(requestsApi.changeRequestStatus).toHaveBeenCalledWith(7, "complete");
    expect(await screen.findByText("Request completed")).toBeInTheDocument();
  });

  it("should show the message of a failed status change", async () => {
    // Test Data
    const user = userEvent.setup();
    mockUser(true);
    vi.mocked(requestsApi.changeRequestStatus).mockRejectedValue(new Error("Please wait a moment"));

    // Test Action
    renderPage(<RequestsPage />, "requests/", "requests/");
    await user.click(await screen.findByRole("button", { name: "Cancel order 7" }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Confirm" }));

    // Expected Result
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("Please wait a moment");
  });

  it("should show the items of an order", async () => {
    // Test Data
    const user = userEvent.setup();
    mockUser(true);
    vi.mocked(requestsApi.loadRequest).mockResolvedValue({
      id: 7,
      status: "OP",
      status_label: "Open",
      requestor: "alice",
      approver: null,
      created: "2026-11-20T10:00:00Z",
      closed: null,
      items: [{ type_id: 587, name: "Rifter", quantity: 3 }],
    });

    // Test Action
    renderPage(<RequestsPage />, "requests/", "requests/");
    await user.click(await screen.findByRole("button", { name: "Show order 7" }));

    // Expected Result
    const dialog = await screen.findByRole("dialog");
    expect(await within(dialog).findByText("Rifter")).toBeInTheDocument();
    expect(within(dialog).getByText("Order for alice - ID: 7")).toBeInTheDocument();
  });
});
