// Third Party
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

// AA Assets
import { renderPage } from "@/__tests__/renderPage";
import { asset, secondAsset } from "@/__tests__/testdata";
import * as assetsApi from "@/Api/calls/assets";
import * as requestsApi from "@/Api/calls/requests";
import { LocationPage } from "@/Pages/LocationPage";

vi.mock("@/Api/calls/assets", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/Api/calls/assets")>();
  return { ...actual, loadAssets: vi.fn() };
});
vi.mock("@/Api/calls/requests", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/Api/calls/requests")>();
  return { ...actual, createOrder: vi.fn() };
});

const renderLocation = (id = "60003760") =>
  renderPage(<LocationPage />, `location/${id}/`, "location/:locationId/");

describe("LocationPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(assetsApi.loadAssets).mockResolvedValue({
      location_id: 60003760,
      location_flag: "all",
      assets: [asset, secondAsset],
    });
  });

  it("should list the assets of the location", async () => {
    // Test Action
    renderLocation();

    // Expected Result
    expect(await screen.findByText("Rifter")).toBeInTheDocument();
    expect(screen.getByText("Reaper")).toBeInTheDocument();
    expect(screen.getByText("N/A")).toBeInTheDocument();
    expect(assetsApi.loadAssets).toHaveBeenCalledWith(60003760);
  });

  it("should show the 404 page for an invalid location", () => {
    // Test Action
    renderLocation("abc");

    // Expected Result
    expect(assetsApi.loadAssets).not.toHaveBeenCalled();
  });

  it("should order one asset limited to the available quantity", async () => {
    // Test Data
    const user = userEvent.setup();
    vi.mocked(requestsApi.createOrder).mockResolvedValue({ success: true, message: "Order created successfully." });

    // Test Action
    renderLocation();
    await user.click(await screen.findByRole("button", { name: "Order Rifter" }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByRole("spinbutton", { name: "Amount of Rifter" }), "9");
    await user.click(within(dialog).getByRole("button", { name: "Confirm" }));

    // Expected Result
    expect(requestsApi.createOrder).toHaveBeenCalledWith([{ asset_pk: 11, amount: 5 }]);
    expect(await screen.findByText("Order created successfully.")).toBeInTheDocument();
  });

  it("should order several assets at once", async () => {
    // Test Data
    const user = userEvent.setup();
    vi.mocked(requestsApi.createOrder).mockResolvedValue({ success: true, message: "Order created successfully." });

    // Test Action
    renderLocation();
    await user.click(await screen.findByRole("button", { name: "Multi Order" }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByRole("spinbutton", { name: "Amount of Rifter" }), "2");
    const reaperRow = within(dialog).getByText("Reaper").closest("tr") as HTMLElement;
    await user.click(within(reaperRow).getByRole("button", { name: "All" }));
    await user.click(within(dialog).getByRole("button", { name: "Confirm" }));

    // Expected Result
    expect(requestsApi.createOrder).toHaveBeenCalledWith([
      { asset_pk: 11, amount: 2 },
      { asset_pk: 12, amount: 2 },
    ]);
  });

  it("should ask for an amount before ordering", async () => {
    // Test Data
    const user = userEvent.setup();

    // Test Action
    renderLocation();
    await user.click(await screen.findByRole("button", { name: "Multi Order" }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Confirm" }));

    // Expected Result
    expect(within(dialog).getByRole("alert")).toHaveTextContent("Enter an amount of at least 1 for one asset.");
    expect(requestsApi.createOrder).not.toHaveBeenCalled();
  });

  it("should close the modal and show the message of a failed order", async () => {
    // Test Data
    const user = userEvent.setup();
    vi.mocked(requestsApi.createOrder).mockRejectedValue(new Error("Requested amount exceeds available quantity."));

    // Test Action
    renderLocation();
    await user.click(await screen.findByRole("button", { name: "Order Rifter" }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "All" }));
    await user.click(within(dialog).getByRole("button", { name: "Confirm" }));

    // Expected Result
    expect(await screen.findByRole("alert")).toHaveTextContent("Requested amount exceeds available quantity.");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(assetsApi.loadAssets).toHaveBeenCalledTimes(2);
  });
});
