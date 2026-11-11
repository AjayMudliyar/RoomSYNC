/* Auto-generated from services/backend/openapi.yaml — do not edit manually. */
export interface paths {
    "/api/v1/auth/csrf": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Issue a CSRF cookie and token for Web SPA unsafe requests. */
        get: operations["auth_csrf_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/email/resend": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Queue verification email resend without disclosing account existence. */
        post: operations["auth_email_resend_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/email/verify": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Consume single-use email verification token and stamp email_verified_at. */
        post: operations["auth_email_verify_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/google": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Verify Google ID token and sign in or create unmerged confirmation challenge. */
        post: operations["auth_google_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/google/link": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Explicitly confirm and prove account ownership before linking a Google identity. */
        post: operations["auth_google_link_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/login": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Authenticate an existing email/password account. */
        post: operations["auth_login_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/logout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Revoke active session family and clear cookies for Web clients. */
        post: operations["auth_logout_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/password/change": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Change authenticated password and revoke all sibling session families. */
        post: operations["auth_password_change_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/password/forgot": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Issue password reset token asynchronously without revealing account existence. */
        post: operations["auth_password_forgot_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/password/reset": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Consume single-use password reset token and invalidate all active sessions. */
        post: operations["auth_password_reset_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/refresh": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Rotate refresh token atomically and detect refresh reuse across web cookies or mobile. */
        post: operations["auth_refresh_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/register": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Register an email/password account (status='active', email_verified_at=None). */
        post: operations["auth_register_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Read or update authenticated user's capability settings (server-enforced). */
        get: operations["me_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** @description Read or update authenticated user's capability settings (server-enforced). */
        patch: operations["me_partial_update"];
        trace?: never;
    };
    "/api/v1/me/data-export": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description Export current user's non-secret account, identity, session, and security records. */
        get: operations["me_data_export_retrieve"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/me/deletion-request": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** @description Request DPDP account deletion requiring explicit phrase confirmation and reauth. */
        post: operations["me_deletion_request_create"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/me/sessions": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** @description List current user's active session families. */
        get: operations["me_sessions_list"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/me/sessions/{session_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** @description Revoke one active session family owned strictly by the authenticated user. */
        delete: operations["me_sessions_destroy"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/system/status": {
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
        AuthSessionData: {
            user: components["schemas"]["AuthUser"];
            platform: components["schemas"]["ClientPlatformEnum"];
            /** Format: uuid */
            session_id: string;
            expires_in_seconds: number;
            tokens?: components["schemas"]["AuthTokens"] | null;
        };
        AuthSessionEnvelope: {
            data: components["schemas"]["AuthSessionData"];
            meta: components["schemas"]["ResponseMeta"];
        };
        AuthTokens: {
            access_token: string;
            refresh_token: string;
            token_type: string;
            expires_in_seconds: number;
        };
        AuthUser: {
            /** Format: uuid */
            id: string;
            /** Format: email */
            email: string;
            phone_e164: string | null;
            status: string;
            email_verified: boolean;
            /** Format: date-time */
            email_verified_at: string | null;
            /** Format: date-time */
            phone_verified_at: string | null;
            /** Format: date-time */
            terms_accepted_at: string | null;
            /** Format: date-time */
            deletion_requested_at: string | null;
            has_usable_password: boolean;
            linked_providers: string[];
            capabilities: components["schemas"]["UserCapabilities"];
            /** Format: date-time */
            created_at: string;
            /** Format: date-time */
            updated_at: string;
        };
        AuthUserEnvelope: {
            data: components["schemas"]["AuthUser"];
            meta: components["schemas"]["ResponseMeta"];
        };
        /**
         * @description * `web` - Web
         *     * `android` - Android
         * @enum {string}
         */
        ClientPlatformEnum: "web" | "android";
        CsrfTokenData: {
            csrf_token: string;
        };
        CsrfTokenEnvelope: {
            data: components["schemas"]["CsrfTokenData"];
            meta: components["schemas"]["ResponseMeta"];
        };
        DataExportData: {
            schema_version: string;
            /** Format: date-time */
            exported_at: string;
            account: components["schemas"]["ExportAccount"];
            oauth_identities: components["schemas"]["ExportOAuthIdentity"][];
            sessions: components["schemas"]["ExportSession"][];
            security_events: components["schemas"]["ExportSecurityEvent"][];
        };
        DataExportEnvelope: {
            data: components["schemas"]["DataExportData"];
            meta: components["schemas"]["ResponseMeta"];
        };
        DeletionRequestEnvelope: {
            data: components["schemas"]["DeletionRequestResponseData"];
            meta: components["schemas"]["ResponseMeta"];
        };
        /** @description Base input serializer rejecting unknown fields with 400 VALIDATION_ERROR. */
        DeletionRequestRequest: {
            confirmation_text: string;
            password?: string;
            google_id_token?: string;
            nonce?: string;
            /** @default false */
            confirm_recent_reauth: boolean;
        };
        DeletionRequestResponseData: {
            deletion_requested: boolean;
            /** Format: date-time */
            deletion_requested_at: string;
        };
        /** @description Base input serializer rejecting unknown fields with 400 VALIDATION_ERROR. */
        EmailResendRequestRequest: {
            /** Format: email */
            email?: string;
        };
        EmailVerifyEnvelope: {
            data: components["schemas"]["EmailVerifyResponseData"];
            meta: components["schemas"]["ResponseMeta"];
        };
        /** @description Base input serializer rejecting unknown fields with 400 VALIDATION_ERROR. */
        EmailVerifyRequestRequest: {
            token: string;
        };
        EmailVerifyResponseData: {
            verified: boolean;
            /** Format: date-time */
            email_verified_at: string;
        };
        ExportAccount: {
            /** Format: uuid */
            id: string;
            /** Format: email */
            email: string;
            phone_e164: string | null;
            status: string;
            /** Format: date-time */
            email_verified_at: string | null;
            /** Format: date-time */
            phone_verified_at: string | null;
            /** Format: date-time */
            terms_accepted_at: string | null;
            /** Format: date-time */
            password_changed_at: string | null;
            /** Format: date-time */
            deletion_requested_at: string | null;
            capabilities: components["schemas"]["UserCapabilities"];
            /** Format: date-time */
            created_at: string;
            /** Format: date-time */
            updated_at: string;
        };
        ExportOAuthIdentity: {
            provider: string;
            /** Format: date-time */
            created_at: string;
            /** Format: date-time */
            last_used_at: string | null;
        };
        ExportSecurityEvent: {
            /** Format: uuid */
            id: string;
            event_type: string;
            outcome: string;
            client_platform: string;
            request_id: string;
            /** Format: date-time */
            created_at: string;
        };
        ExportSession: {
            /** Format: uuid */
            id: string;
            client_platform: string;
            device_label: string;
            /** Format: date-time */
            created_at: string;
            /** Format: date-time */
            last_used_at: string | null;
            /** Format: date-time */
            expires_at: string;
            /** Format: date-time */
            revoked_at: string | null;
        };
        GenericAcceptedData: {
            accepted: boolean;
            message: string;
        };
        GenericAcceptedEnvelope: {
            data: components["schemas"]["GenericAcceptedData"];
            meta: components["schemas"]["ResponseMeta"];
        };
        /** @description Base input serializer rejecting unknown fields with 400 VALIDATION_ERROR. */
        GoogleAuthRequestRequest: {
            id_token: string;
            nonce: string;
            accept_terms?: boolean;
            confirm_adult?: boolean;
            device_label?: string;
        };
        /** @description Base input serializer rejecting unknown fields with 400 VALIDATION_ERROR. */
        GoogleLinkRequestRequest: {
            link_challenge_token: string;
            confirm_link: boolean;
            password?: string;
            email_verification_token?: string;
            device_label?: string;
        };
        /** @description Base input serializer rejecting unknown fields with 400 VALIDATION_ERROR. */
        LoginRequestRequest: {
            /** Format: email */
            email: string;
            password: string;
            device_label?: string;
        };
        LogoutEnvelope: {
            data: components["schemas"]["LogoutResponseData"];
            meta: components["schemas"]["ResponseMeta"];
        };
        /** @description Base input serializer rejecting unknown fields with 400 VALIDATION_ERROR. */
        LogoutRequestRequest: {
            refresh_token?: string;
        };
        LogoutResponseData: {
            logged_out: boolean;
        };
        PasswordChangeEnvelope: {
            data: components["schemas"]["PasswordChangeResponseData"];
            meta: components["schemas"]["ResponseMeta"];
        };
        /** @description Base input serializer rejecting unknown fields with 400 VALIDATION_ERROR. */
        PasswordChangeRequestRequest: {
            current_password?: string;
            new_password: string;
        };
        PasswordChangeResponseData: {
            password_changed: boolean;
        };
        /** @description Base input serializer rejecting unknown fields with 400 VALIDATION_ERROR. */
        PasswordForgotRequestRequest: {
            /** Format: email */
            email: string;
        };
        PasswordResetEnvelope: {
            data: components["schemas"]["PasswordResetResponseData"];
            meta: components["schemas"]["ResponseMeta"];
        };
        /** @description Base input serializer rejecting unknown fields with 400 VALIDATION_ERROR. */
        PasswordResetRequestRequest: {
            token: string;
            new_password: string;
        };
        PasswordResetResponseData: {
            password_reset: boolean;
        };
        /** @description Base input serializer rejecting unknown fields with 400 VALIDATION_ERROR. */
        PatchedMeUpdateRequestRequest: {
            can_seek_room?: boolean;
            can_offer_room?: boolean;
            can_list_property?: boolean;
        };
        /** @description Base input serializer rejecting unknown fields with 400 VALIDATION_ERROR. */
        RefreshRequestRequest: {
            refresh_token?: string;
            device_label?: string;
        };
        /** @description Base input serializer rejecting unknown fields with 400 VALIDATION_ERROR. */
        RegisterRequestRequest: {
            /** Format: email */
            email: string;
            password: string;
            accept_terms: boolean;
            confirm_adult: boolean;
            device_label?: string;
        };
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
        UserCapabilities: {
            can_seek_room: boolean;
            can_offer_room: boolean;
            can_list_property: boolean;
        };
        UserSessionItem: {
            /** Format: uuid */
            id: string;
            client_platform: components["schemas"]["ClientPlatformEnum"];
            device_label: string;
            /** Format: date-time */
            created_at: string;
            /** Format: date-time */
            last_used_at: string | null;
            /** Format: date-time */
            expires_at: string;
            is_current: boolean;
        };
        UserSessionListEnvelope: {
            data: components["schemas"]["UserSessionItem"][];
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
    auth_csrf_retrieve: {
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
                    "application/json": components["schemas"]["CsrfTokenEnvelope"];
                };
            };
        };
    };
    auth_email_resend_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["EmailResendRequestRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["EmailResendRequestRequest"];
                "multipart/form-data": components["schemas"]["EmailResendRequestRequest"];
            };
        };
        responses: {
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GenericAcceptedEnvelope"];
                };
            };
        };
    };
    auth_email_verify_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["EmailVerifyRequestRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["EmailVerifyRequestRequest"];
                "multipart/form-data": components["schemas"]["EmailVerifyRequestRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["EmailVerifyEnvelope"];
                };
            };
        };
    };
    auth_google_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["GoogleAuthRequestRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["GoogleAuthRequestRequest"];
                "multipart/form-data": components["schemas"]["GoogleAuthRequestRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuthSessionEnvelope"];
                };
            };
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuthSessionEnvelope"];
                };
            };
        };
    };
    auth_google_link_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["GoogleLinkRequestRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["GoogleLinkRequestRequest"];
                "multipart/form-data": components["schemas"]["GoogleLinkRequestRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuthSessionEnvelope"];
                };
            };
        };
    };
    auth_login_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LoginRequestRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["LoginRequestRequest"];
                "multipart/form-data": components["schemas"]["LoginRequestRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuthSessionEnvelope"];
                };
            };
        };
    };
    auth_logout_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["LogoutRequestRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["LogoutRequestRequest"];
                "multipart/form-data": components["schemas"]["LogoutRequestRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LogoutEnvelope"];
                };
            };
        };
    };
    auth_password_change_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PasswordChangeRequestRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["PasswordChangeRequestRequest"];
                "multipart/form-data": components["schemas"]["PasswordChangeRequestRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PasswordChangeEnvelope"];
                };
            };
        };
    };
    auth_password_forgot_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PasswordForgotRequestRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["PasswordForgotRequestRequest"];
                "multipart/form-data": components["schemas"]["PasswordForgotRequestRequest"];
            };
        };
        responses: {
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GenericAcceptedEnvelope"];
                };
            };
        };
    };
    auth_password_reset_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PasswordResetRequestRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["PasswordResetRequestRequest"];
                "multipart/form-data": components["schemas"]["PasswordResetRequestRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PasswordResetEnvelope"];
                };
            };
        };
    };
    auth_refresh_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["RefreshRequestRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["RefreshRequestRequest"];
                "multipart/form-data": components["schemas"]["RefreshRequestRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuthSessionEnvelope"];
                };
            };
        };
    };
    auth_register_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RegisterRequestRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["RegisterRequestRequest"];
                "multipart/form-data": components["schemas"]["RegisterRequestRequest"];
            };
        };
        responses: {
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuthSessionEnvelope"];
                };
            };
        };
    };
    me_retrieve: {
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
                    "application/json": components["schemas"]["AuthUserEnvelope"];
                };
            };
        };
    };
    me_partial_update: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: {
            content: {
                "application/json": components["schemas"]["PatchedMeUpdateRequestRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["PatchedMeUpdateRequestRequest"];
                "multipart/form-data": components["schemas"]["PatchedMeUpdateRequestRequest"];
            };
        };
        responses: {
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuthUserEnvelope"];
                };
            };
        };
    };
    me_data_export_retrieve: {
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
                    "application/json": components["schemas"]["DataExportEnvelope"];
                };
            };
        };
    };
    me_deletion_request_create: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["DeletionRequestRequest"];
                "application/x-www-form-urlencoded": components["schemas"]["DeletionRequestRequest"];
                "multipart/form-data": components["schemas"]["DeletionRequestRequest"];
            };
        };
        responses: {
            202: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DeletionRequestEnvelope"];
                };
            };
        };
    };
    me_sessions_list: {
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
                    "application/json": components["schemas"]["UserSessionListEnvelope"];
                };
            };
        };
    };
    me_sessions_destroy: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                session_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description No response body */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
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
