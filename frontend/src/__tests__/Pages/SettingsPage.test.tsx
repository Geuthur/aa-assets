// Third Party
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useUserSettings } from "aa-geuthur-react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// AA Assets
import { SettingsPage } from "@/Pages/SettingsPage";

// The hook itself (request, optimistic update, rollback) is tested in aa-geuthur-react.
vi.mock("aa-geuthur-react", async (importOriginal) => {
  const actual = await importOriginal<typeof import("aa-geuthur-react")>();
  return { ...actual, useUserSettings: vi.fn() };
});

type HookResult = ReturnType<typeof useUserSettings>;

const mutate = vi.fn();

/** Sets what `useUserSettings` returns for the page. */
const mockSettings = (result: object, mutation: object = {}) => {
  vi.mocked(useUserSettings).mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
    ...result,
    updateMutation: { mutate, isError: false, isPending: false, ...mutation },
  } as unknown as HookResult);
};

describe("SettingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should show the loader while the settings load", () => {
    // Test Data
    mockSettings({ isLoading: true });

    // Test Action
    render(<SettingsPage />);

    // Expected Result
    expect(screen.getByText("Loading settings...")).toBeInTheDocument();
    expect(screen.queryByRole("switch")).not.toBeInTheDocument();
  });

  it("should show an error when the settings cannot be loaded", () => {
    // Test Data
    mockSettings({ isError: true });

    // Test Action
    render(<SettingsPage />);

    // Expected Result
    expect(screen.getByRole("alert")).toHaveTextContent("Failed to load settings. Please try refreshing the page.");
  });

  it("should load the saved global notification preference", () => {
    // Test Data
    mockSettings({ data: { disable_notifications: true } });

    // Test Action
    render(<SettingsPage />);

    // Expected Result
    expect(screen.getByRole("switch", { name: "Disable all notifications" })).toBeChecked();
  });

  it("should save the global preference when the switch is enabled", async () => {
    // Test Data
    const user = userEvent.setup();
    mockSettings({ data: { disable_notifications: false } });

    // Test Action
    render(<SettingsPage />);
    await user.click(screen.getByRole("switch", { name: "Disable all notifications" }));

    // Expected Result
    expect(mutate).toHaveBeenCalledWith({ disable_notifications: true });
  });

  it("should lock the switch while the setting is saved", () => {
    // Test Data
    mockSettings({ data: { disable_notifications: true } }, { isPending: true });

    // Test Action
    render(<SettingsPage />);

    // Expected Result
    expect(screen.getByRole("switch", { name: "Disable all notifications" })).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent("Saving...");
  });

  it("should tell the user when the setting could not be saved", () => {
    // Test Data
    mockSettings({ data: { disable_notifications: false } }, { isError: true });

    // Test Action
    render(<SettingsPage />);

    // Expected Result
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Could not save this setting. Your previous preference was restored.",
    );
  });
});
