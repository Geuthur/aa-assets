// Third Party
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

// AA Assets
import { renderPage } from "@/__tests__/renderPage";
import { location, owner, ownerDetail } from "@/__tests__/testdata";
import * as assetsApi from "@/Api/calls/assets";
import { MainPage } from "@/Pages/MainPage";

vi.mock("@/Api/calls/assets", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/Api/calls/assets")>();
  return { ...actual, loadLocations: vi.fn(), loadOwners: vi.fn(), loadOwner: vi.fn() };
});

describe("MainPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should list the locations with a link to their assets", async () => {
    // Test Data
    vi.mocked(assetsApi.loadLocations).mockResolvedValue([location]);
    vi.mocked(assetsApi.loadOwners).mockResolvedValue([owner]);

    // Test Action
    renderPage(<MainPage />);

    // Expected Result
    const link = await screen.findByRole("link", { name: "Jita IV - Moon 4" });
    expect(link).toHaveAttribute("href", "/assets/location/60003760/");
    expect(screen.getByText("Jita")).toBeInTheDocument();
  });

  it("should list the owners with their status", async () => {
    // Test Data
    vi.mocked(assetsApi.loadLocations).mockResolvedValue([]);
    vi.mocked(assetsApi.loadOwners).mockResolvedValue([owner]);

    // Test Action
    renderPage(<MainPage />);

    // Expected Result
    expect(await screen.findByText("Alpha Corp")).toBeInTheDocument();
    expect(screen.getByTestId("owner-status-badge")).toHaveAttribute("data-status", "ok");
  });

  it("should show the status of every section of an owner", async () => {
    // Test Data
    const user = userEvent.setup();
    vi.mocked(assetsApi.loadLocations).mockResolvedValue([]);
    vi.mocked(assetsApi.loadOwners).mockResolvedValue([owner]);
    vi.mocked(assetsApi.loadOwner).mockResolvedValue(ownerDetail);

    // Test Action
    renderPage(<MainPage />);
    await user.click(await screen.findByRole("button", { name: "Update status of Alpha Corp" }));

    // Expected Result
    const dialog = await screen.findByRole("dialog");
    expect(await within(dialog).findByText("ESI is down")).toBeInTheDocument();
    expect(assetsApi.loadOwner).toHaveBeenCalledWith(1);
  });
});
