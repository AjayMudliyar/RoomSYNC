/* Auto-generated from services/backend/openapi.yaml — do not edit manually. */
export interface paths {
    "/api/v1/system/status/": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Minimal M0 public system status endpoint verifying DRF envelopes and OpenAPI generation. */
        get: operations["system_status_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        ResponseMeta: {
            request_id: string;
        };
        SystemStatusData: {
            service: string;
            status: string;
            api_version: string;
        };
        SystemStatusEnvelope: {
            data: components["schemas"]["SystemStatusData"];
            meta: components["schemas"]["ResponseMeta"];
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    system_status_retrieve: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SystemStatusEnvelope"];
                };
            };
        };
    };
}
