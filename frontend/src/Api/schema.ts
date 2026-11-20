// AA Assets
import type { components } from "@/Api/OpenApi";

// General
export type ErrorSchema = components['schemas']['ErrorSchema']
export type ActionResponse = components['schemas']['ActionResponse']
export type MenuSchema = components['schemas']['MenuSchema']
export type UserData = components['schemas']['UserData']
export type UserSettingsSchema = components['schemas']['UserSettingsSchema']
export type UserSettingsUpdateRequest = components['schemas']['UserSettingsUpdateRequest']
export type AdminTasksRequest = components['schemas']['AdminTasksRequest']

// Owners
export type OwnerSchema = components['schemas']['OwnerSchema']
export type OwnerDetailSchema = components['schemas']['OwnerDetailSchema']
export type OwnerUpdateStatusSchema = components['schemas']['OwnerUpdateStatusSchema']

// Locations and assets
export type LocationSchema = components['schemas']['LocationSchema']
export type AssetSchema = components['schemas']['AssetSchema']
export type AssetsSchema = components['schemas']['Assets']

// Requests
export type RequestSchema = components['schemas']['Requests']
export type RequestDetailSchema = components['schemas']['RequestDetailSchema']
export type RequestItemSchema = components['schemas']['RequestItemSchema']
export type OrderItemRequest = components['schemas']['OrderItemRequest']
