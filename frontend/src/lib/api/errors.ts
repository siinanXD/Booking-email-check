/** Extract API error codes from Axios-style errors. */

export function getApiErrorCode(err: unknown): string | undefined {
  const code = (err as { response?: { data?: { code?: unknown } } })?.response
    ?.data?.code;
  return typeof code === "string" ? code : undefined;
}
