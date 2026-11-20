// Third Party
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useUserData } from "aa-geuthur-react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// AA Assets
import { renderPage } from "@/__tests__/renderPage";
import * as adminApi from "@/Api/calls/admin";
import { AdminPage } from "@/Pages/AdminPage";

vi.mock("aa-geuthur-react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("aa-geuthur-react")>();
  return { ...actual, useUserData: vi.fn() };
});
vi.mock("@/Api/calls/admin", () => ({ queueAdminTasks: vi.fn() }));

const mockUser = (isAdmin: boolean) =>
  vi.mocked(useUserData).mockReturnValue({
    data: { user: { is_admin: isAdmin } },
    isLoading: false,
  } as unknown as ReturnType<typeof useUserData>);

describe("AdminPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should not show the tasks to other users", () => {
    // Test Data
    mockUser(false);

    // Test Action
    renderPage(<AdminPage />, "admin/", "admin/");

    // Expected Result
    expect(screen.queryByRole("button", { name: "Submit" })).not.toBeInTheDocument();
  });

  it("should queue the selected tasks", async () => {
    // Test Data
    const user = userEvent.setup();
    mockUser(true);
    vi.mocked(adminApi.queueAdminTasks).mockResolvedValue({ success: true, message: "Queued Update All Assets" });

    // Test Action
    renderPage(<AdminPage />, "admin/", "admin/");
    await user.click(screen.getByRole("checkbox", { name: "Mark all tasks as Force Refresh" }));
    await user.click(screen.getByRole("checkbox", { name: "Update All Assets" }));
    await user.click(screen.getByRole("button", { name: "Submit" }));

    // Expected Result
    expect(adminApi.queueAdminTasks).toHaveBeenCalledWith(
      expect.objectContaining({ force_refresh: true, update_assets: true, clear_etags: false }),
    );
    expect(await screen.findByText("Queued Update All Assets")).toBeInTheDocument();
  });

  it("should show the message of a failed request", async () => {
    // Test Data
    const user = userEvent.setup();
    mockUser(true);
    vi.mocked(adminApi.queueAdminTasks).mockRejectedValue(new Error("Permission Denied"));

    // Test Action
    renderPage(<AdminPage />, "admin/", "admin/");
    await user.click(screen.getByRole("button", { name: "Submit" }));

    // Expected Result
    expect(await screen.findByRole("alert")).toHaveTextContent("Permission Denied");
  });
});
