// AA Assets
import type { AssetSchema, LocationSchema, OwnerDetailSchema, OwnerSchema, RequestSchema } from "@/Api/schema";

export const owner: OwnerSchema = {
  id: 1,
  name: "Alpha Corp",
  owner_type: "corporation",
  character_id: null,
  corporation_id: 2001,
  active: true,
  update_status: "ok",
  update_status_label: "OK",
  last_update: null,
};

export const ownerDetail: OwnerDetailSchema = {
  ...owner,
  sections: [
    {
      section: "assets",
      section_label: "Assets",
      is_success: false,
      has_token_error: false,
      error_message: "ESI is down",
      last_run_finished_at: null,
      last_update_finished_at: null,
    },
  ],
};

export const location: LocationSchema = {
  location_id: 60003760,
  name: "Jita IV - Moon 4",
  solar_system: "Jita",
};

export const asset: AssetSchema = {
  asset_pk: 11,
  item_id: 1000001,
  type_id: 587,
  name: "Rifter",
  quantity: 5,
  location_id: 60003760,
  location: "Jita IV - Moon 4",
  location_flag: "Hangar",
  price: 1500000,
};

export const secondAsset: AssetSchema = {
  ...asset,
  asset_pk: 12,
  item_id: 1000002,
  type_id: 588,
  name: "Reaper",
  quantity: 2,
  price: null,
};

export const request: RequestSchema = {
  id: 7,
  status: "Open",
  action: "OP",
  created: "2026-11-20T10:00:00Z",
  closed: null,
  approver: null,
  requestor: "alice",
  can_cancel: true,
  can_complete: true,
  can_reopen: false,
};
