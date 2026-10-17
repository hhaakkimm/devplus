import { createApiClient } from "@devplus/api-client";
import { cookies } from "next/headers";

export async function serverApi(): Promise<ReturnType<typeof createApiClient>> {
  // Read cookies first: that marks the route dynamic before the check below can fail a build.
  const cookie = (await cookies()).toString();
  const baseUrl = process.env.API_INTERNAL_URL;
  if (!baseUrl) throw new Error("API_INTERNAL_URL is not set");
  return createApiClient(baseUrl, { cookie });
}
