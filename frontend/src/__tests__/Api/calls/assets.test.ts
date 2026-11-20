// Third Party
import { beforeEach, describe, expect, it, vi } from "vitest";

// AA Assets
import { asset, location, owner, ownerDetail } from "@/__tests__/testdata";
import { apiClient } from "@/Api/Api";
import { assetsQueryKeys, loadAssets, loadLocations, loadOwner, loadOwners } from "@/Api/calls/assets";
import { ProjectName } from "@/constants";

const ok = (data: unknown) => ({ data, error: undefined, response: new Response() }) as never;
const failed = (error: unknown) => ({ data: undefined, error, response: new Response() }) as never;

describe("Assets API calls", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("should build the query keys", () => {
    // Test Action & Expected Result
    expect(assetsQueryKeys.owners).toEqual(["Owners"]);
    expect(assetsQueryKeys.owner(1)).toEqual(["Owners", 1]);
    expect(assetsQueryKeys.locations).toEqual(["Locations"]);
    expect(assetsQueryKeys.assets(5)).toEqual(["Assets", 5]);
  });

  it("should load the owners", async () => {
    // Test Data
    vi.spyOn(apiClient, "GET").mockResolvedValueOnce(ok([owner]));

    // Test Action
    const result = await loadOwners();

    // Expected Result
    expect(result).toEqual([owner]);
    expect(apiClient.GET).toHaveBeenCalledWith(`/${ProjectName}/api/owners/`);
  });

  it("should load one owner", async () => {
    // Test Data
    vi.spyOn(apiClient, "GET").mockResolvedValueOnce(ok(ownerDetail));

    // Test Action
    const result = await loadOwner(1);

    // Expected Result
    expect(result).toEqual(ownerDetail);
    expect(apiClient.GET).toHaveBeenCalledWith(`/${ProjectName}/api/owners/{owner_id}/`, {
      params: { path: { owner_id: 1 } },
    });
  });

  it("should load the locations", async () => {
    // Test Data
    vi.spyOn(apiClient, "GET").mockResolvedValueOnce(ok([location]));

    // Test Action
    const result = await loadLocations();

    // Expected Result
    expect(result).toEqual([location]);
  });

  it("should load all assets of a location", async () => {
    // Test Data
    const payload = { location_id: 60003760, location_flag: "all", assets: [asset] };
    vi.spyOn(apiClient, "GET").mockResolvedValueOnce(ok(payload));

    // Test Action
    const result = await loadAssets(60003760);

    // Expected Result
    expect(result).toEqual(payload);
    expect(apiClient.GET).toHaveBeenCalledWith(`/${ProjectName}/api/location/{location_id}/flag/{location_flag}/`, {
      params: { path: { location_id: 60003760, location_flag: "all" } },
    });
  });

  it("should throw the message of the API when a request fails", async () => {
    // Test Data
    vi.spyOn(apiClient, "GET").mockResolvedValue(failed({ error: "Permission Denied" }));

    // Test Action & Expected Result
    await expect(loadOwners()).rejects.toThrow("Permission Denied");
    await expect(loadOwner(1)).rejects.toThrow("Permission Denied");
    await expect(loadLocations()).rejects.toThrow("Permission Denied");
    await expect(loadAssets(1)).rejects.toThrow("Permission Denied");
  });
});
