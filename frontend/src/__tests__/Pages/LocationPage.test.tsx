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

const renderLocation = (id = "60003760", search = "") =>
  renderPage(<LocationPage />, `location/${id}/${search}`, "location/:locationId/");

describe("LocationPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(assetsApi.loadAssets).mockResolvedValue({
      location_id: 60003760,
      location_flag: "all",
      assets: [asset, secondAsset],
    });
  });

  it("should prefilter the location flag from the query parameter", async () => {
    // Test Data
    vi.mocked(assetsApi.loadAssets).mockResolvedValue({
      location_id: 60003760,
      location_flag: "all",
      assets: [asset, { ...secondAsset, location_flag: "Corp Security Access Group 5", location_flag_code: "CorpSAG5" }],
    });

    // Test Action
    renderLocation("60003760", "?flag=CorpSAG5");

    // Expected Result
    expect(await screen.findByText("Reaper")).toBeInTheDocument();
    expect(screen.queryByText("Rifter")).not.toBeInTheDocument();
    expect(screen.getByDisplayValue("Corp Security Access Group 5")).toBeInTheDocument();
  });

  it("should show no asset for a location flag without assets", async () => {
    // Test Data
    vi.mocked(assetsApi.loadAssets).mockResolvedValue({
      location_id: 60003760,
      location_flag: "all",
      assets: [asset, { ...secondAsset, location_flag: "Corp Security Access Group 5", location_flag_code: "CorpSAG5" }],
    });

    // Test Action
    renderLocation("60003760", "?flag=CorpSAG1");

    // Expected Result
    expect(await screen.findByText("No assets found at this location.")).toBeInTheDocument();
    expect(screen.queryByText("Reaper")).not.toBeInTheDocument();
    expect(screen.queryByText("Rifter")).not.toBeInTheDocument();
  });

  it("should filter the location flag by the typed label", async () => {
    // Test Data
    const user = userEvent.setup();
    vi.mocked(assetsApi.loadAssets).mockResolvedValue({
      location_id: 60003760,
      location_flag: "all",
      assets: [asset, { ...secondAsset, location_flag: "Corp Security Access Group 5", location_flag_code: "CorpSAG5" }],
    });

    // Test Action
    renderLocation();
    expect(await screen.findByText("Rifter")).toBeInTheDocument();
    const flagFilter = screen.getAllByPlaceholderText("Filter…")[2];
    await user.type(flagFilter, "security");

    // Expected Result
    expect(screen.getByText("Reaper")).toBeInTheDocument();
    expect(screen.queryByText("Rifter")).not.toBeInTheDocument();
  });

  it("should not filter the location flag without the query parameter", async () => {
    // Test Data
    vi.mocked(assetsApi.loadAssets).mockResolvedValue({
      location_id: 60003760,
      location_flag: "all",
      assets: [asset, { ...secondAsset, location_flag: "Corp Security Access Group 5", location_flag_code: "CorpSAG5" }],
    });

    // Test Action
    renderLocation();

    // Expected Result
    expect(await screen.findByText("Reaper")).toBeInTheDocument();
    expect(screen.getByText("Rifter")).toBeInTheDocument();
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

  it("should add an asset with its whole quantity and order the cart", async () => {
    // Test Data
    const user = userEvent.setup();
    vi.mocked(requestsApi.createOrder).mockResolvedValue({ success: true, message: "Order created successfully." });

    // Test Action
    renderLocation();
    await user.click(await screen.findByRole("button", { name: "Add Rifter to order" }));
    await user.click(screen.getByRole("button", { name: "Add Reaper to order" }));
    expect(screen.getByText("Order cart: 2 assets")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Review Order" }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Place Order" }));

    // Expected Result
    expect(requestsApi.createOrder).toHaveBeenCalledWith([
      { asset_pk: 11, amount: 5 },
      { asset_pk: 12, amount: 2 },
    ]);
    expect(await screen.findByText("Order created successfully.")).toBeInTheDocument();
    expect(screen.queryByText(/Order cart:/)).not.toBeInTheDocument();
  });

  it("should take an asset out of the cart on the second click", async () => {
    // Test Data
    const user = userEvent.setup();

    // Test Action
    renderLocation();
    await user.click(await screen.findByRole("button", { name: "Add Rifter to order" }));
    await user.click(screen.getByRole("button", { name: "Remove Rifter from order" }));

    // Expected Result
    expect(screen.getByRole("button", { name: "Add Rifter to order" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Review Order" })).not.toBeInTheDocument();
  });

  it("should limit the amount in the review to the available quantity", async () => {
    // Test Data
    const user = userEvent.setup();
    vi.mocked(requestsApi.createOrder).mockResolvedValue({ success: true, message: "Order created successfully." });

    // Test Action
    renderLocation();
    await user.click(await screen.findByRole("button", { name: "Add Rifter to order" }));
    await user.click(screen.getByRole("button", { name: "Review Order" }));
    const dialog = await screen.findByRole("dialog");
    const amount = within(dialog).getByRole("spinbutton", { name: "Amount of Rifter" });
    expect(amount).toHaveValue(5);
    await user.clear(amount);
    await user.type(amount, "3");
    await user.click(within(dialog).getByRole("button", { name: "Place Order" }));

    // Expected Result
    expect(requestsApi.createOrder).toHaveBeenCalledWith([{ asset_pk: 11, amount: 3 }]);
  });

  it("should not order an asset with an empty amount", async () => {
    // Test Data
    const user = userEvent.setup();

    // Test Action
    renderLocation();
    await user.click(await screen.findByRole("button", { name: "Add Rifter to order" }));
    await user.click(screen.getByRole("button", { name: "Review Order" }));
    const dialog = await screen.findByRole("dialog");
    await user.clear(within(dialog).getByRole("spinbutton", { name: "Amount of Rifter" }));

    // Expected Result
    expect(within(dialog).getByRole("button", { name: "Place Order" })).toBeDisabled();
  });

  it("should remove an asset in the review and clear the cart", async () => {
    // Test Data
    const user = userEvent.setup();

    // Test Action
    renderLocation();
    await user.click(await screen.findByRole("button", { name: "Add Rifter to order" }));
    await user.click(screen.getByRole("button", { name: "Add Reaper to order" }));
    await user.click(screen.getByRole("button", { name: "Review Order" }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Remove Rifter from order" }));
    expect(within(dialog).queryByText("Rifter")).not.toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    await user.click(screen.getByRole("button", { name: "Clear selection" }));

    // Expected Result
    expect(screen.queryByText(/Order cart:/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add Reaper to order" })).toBeInTheDocument();
  });

  it("should not show the multi order button anymore", async () => {
    // Test Action
    renderLocation();

    // Expected Result
    expect(await screen.findByText("Rifter")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Multi Order" })).not.toBeInTheDocument();
  });

  it("should close the review, empty the cart and show the message of a failed order", async () => {
    // Test Data
    const user = userEvent.setup();
    vi.mocked(requestsApi.createOrder).mockRejectedValue(new Error("Requested amount exceeds available quantity."));

    // Test Action
    renderLocation();
    await user.click(await screen.findByRole("button", { name: "Add Rifter to order" }));
    await user.click(screen.getByRole("button", { name: "Review Order" }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Place Order" }));

    // Expected Result
    expect(await screen.findByRole("alert")).toHaveTextContent("Requested amount exceeds available quantity.");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.queryByText(/Order cart:/)).not.toBeInTheDocument();
    expect(assetsApi.loadAssets).toHaveBeenCalledTimes(2);
  });
});
