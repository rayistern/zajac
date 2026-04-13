import createFetchClient from "openapi-fetch";
import createClient from "openapi-react-query";
import type { paths } from "./types/backend-schema";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim() || "";

export const fetchClient = createFetchClient<paths>({
  baseUrl: apiBaseUrl,
});
// tanstack-query client
export const $api = createClient(fetchClient);
