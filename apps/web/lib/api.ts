import { createApiClient } from "@devplus/api-client";
import { cookies } from "next/headers";

export async function serverApi(): Promise<ReturnType<typeof createApiClient>> {
  return createApiClient(process.env.API_INTERNAL_URL!, {
    cookie: (await cookies()).toString(),
  });
}
