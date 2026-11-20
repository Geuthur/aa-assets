// Third Party
import { apiErrorMessage } from "aa-geuthur-react";

// AA Assets
import { apiClient } from "@/Api/Api";
import type { AdminTasksRequest, ActionResponse } from "@/Api/schema";
import { ProjectName } from "@/constants";

export async function queueAdminTasks(tasks: AdminTasksRequest): Promise<ActionResponse> {
  const { data, error } = await apiClient.POST(`/${ProjectName}/api/admin/tasks/`, { body: tasks });
  if (error || !data) {
    throw new Error(apiErrorMessage(error, "Failed to queue the tasks"));
  }
  return data;
}
