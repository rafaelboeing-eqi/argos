const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function fetchJson<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`);
  } catch (cause) {
    throw new ApiError(`Failed to reach the Argos backend: ${String(cause)}`);
  }

  if (!response.ok) {
    throw new ApiError(`Argos backend returned HTTP ${response.status} for ${path}`, response.status);
  }

  return (await response.json()) as T;
}
