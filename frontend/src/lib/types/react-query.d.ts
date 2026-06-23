import "@tanstack/react-query";

declare module "@tanstack/react-query" {
  interface Register {
    queryMeta: { skipGlobalError?: boolean };
    mutationMeta: { skipGlobalError?: boolean };
  }
}
