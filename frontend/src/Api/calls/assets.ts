// Third Party
import { apiErrorMessage } from "aa-geuthur-react";

// AA Assets
import { apiClient } from "@/Api/Api";
import type { AssetsSchema, LocationSchema, OwnerDetailSchema, OwnerSchema } from "@/Api/schema";
import { ProjectName } from "@/constants";

/*
 * A failed request throws the message of the API (`{"error": …}`) so the user reads the reason,
 * and the fixed text only when the API sent none.
 */

/** Query keys of owners, locations and assets. */
export const assetsQueryKeys = {
  owners: ["Owners"] as const,
  owner: (ownerId: number) => ["Owners", ownerId] as const,
  locations: ["Locations"] as const,
  assets: (locationId: number) => ["Assets", locationId] as const,
};

export async function loadOwners(): Promise<OwnerSchema[]> {
  const { data, error } = await apiClient.GET(`/${ProjectName}/api/owners/`);
  if (error || !data) {
    throw new Error(apiErrorMessage(error, "Failed to load owners"));
  }
  return data;
}

export async function loadOwner(ownerId: number): Promise<OwnerDetailSchema> {
  const { data, error } = await apiClient.GET(`/${ProjectName}/api/owners/{owner_id}/`, {
    params: { path: { owner_id: ownerId } },
  });
  if (error || !data) {
    throw new Error(apiErrorMessage(error, "Failed to load owner"));
  }
  return data;
}

export async function loadLocations(): Promise<LocationSchema[]> {
  const { data, error } = await apiClient.GET(`/${ProjectName}/api/location/`);
  if (error || !data) {
    throw new Error(apiErrorMessage(error, "Failed to load locations"));
  }
  return data;
}

export async function loadAssets(locationId: number): Promise<AssetsSchema> {
  const { data, error } = await apiClient.GET(
    `/${ProjectName}/api/location/{location_id}/flag/{location_flag}/`,
    { params: { path: { location_id: locationId, location_flag: "all" } } },
  );
  if (error || !data) {
    throw new Error(apiErrorMessage(error, "Failed to load assets"));
  }
  return data;
}
