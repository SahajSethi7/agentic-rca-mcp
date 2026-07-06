import { Auth0Provider, useAuth0 } from "@auth0/auth0-react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export const AUTH_PERMISSIONS = {
  read: "rca:read",
  write: "rca:write",
  download: "rca:download",
  audit: "rca:audit",
  admin: "rca:admin",
} as const;

const AUTH_SCOPE = Object.values(AUTH_PERMISSIONS).join(" ");

function envFlag(value: string | undefined, fallback: boolean) {
  if (value == null || value === "") return fallback;
  return ["1", "true", "yes", "on"].includes(value.toLowerCase());
}

const domain = import.meta.env.VITE_AUTH0_DOMAIN || "";
const clientId = import.meta.env.VITE_AUTH0_CLIENT_ID || "";
const audience = import.meta.env.VITE_AUTH0_AUDIENCE || "";
const configured = Boolean(domain && clientId && audience);
const enabled = envFlag(import.meta.env.VITE_AUTH_ENABLED, configured);

export const authConfig = {
  enabled,
  configured,
  domain,
  clientId,
  audience,
  scope: AUTH_SCOPE,
};

export interface AppUser {
  sub?: string;
  name?: string;
  email?: string;
  picture?: string;
}

export interface AppAuthContext {
  enabled: boolean;
  configured: boolean;
  isLoading: boolean;
  isAuthenticated: boolean;
  user?: AppUser;
  permissions: string[];
  error: string | null;
  login: () => Promise<void>;
  logout: () => void;
  getAccessToken: () => Promise<string | null>;
  hasPermission: (permission: string) => boolean;
}

const noopAsync = async () => undefined;

const AuthContext = createContext<AppAuthContext>({
  enabled: false,
  configured: false,
  isLoading: false,
  isAuthenticated: false,
  permissions: [],
  error: null,
  login: noopAsync,
  logout: () => undefined,
  getAccessToken: async () => null,
  hasPermission: () => true,
});

function parseJwtClaims(token: string): Record<string, unknown> {
  const [, payload] = token.split(".");
  if (!payload) return {};
  const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
  const json = decodeURIComponent(
    window
      .atob(normalized)
      .split("")
      .map((char) => `%${char.charCodeAt(0).toString(16).padStart(2, "0")}`)
      .join(""),
  );
  return JSON.parse(json) as Record<string, unknown>;
}

function permissionsFromClaims(claims: Record<string, unknown>) {
  const permissions = new Set<string>();
  const rawPermissions = claims.permissions;
  if (Array.isArray(rawPermissions)) {
    rawPermissions.forEach((permission) => {
      if (typeof permission === "string") permissions.add(permission);
    });
  }
  const rawScope = claims.scope;
  if (typeof rawScope === "string") {
    rawScope.split(/\s+/).forEach((permission) => {
      if (permission) permissions.add(permission);
    });
  }
  return [...permissions].sort();
}

function StaticAuthProvider({
  children,
  configError = null,
}: {
  children: ReactNode;
  configError?: string | null;
}) {
  const value = useMemo<AppAuthContext>(
    () => ({
      enabled: authConfig.enabled,
      configured: authConfig.configured,
      isLoading: false,
      isAuthenticated: !authConfig.enabled,
      permissions: [],
      error: configError,
      login: noopAsync,
      logout: () => undefined,
      getAccessToken: async () => null,
      hasPermission: () => !authConfig.enabled,
    }),
    [configError],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

function AuthBridge({ children }: { children: ReactNode }) {
  const {
    error,
    getAccessTokenSilently,
    isAuthenticated,
    isLoading,
    loginWithRedirect,
    logout,
    user,
  } = useAuth0();
  const [permissions, setPermissions] = useState<string[]>([]);
  const [permissionsLoaded, setPermissionsLoaded] = useState(false);
  const [tokenError, setTokenError] = useState<string | null>(null);

  const getAccessToken = useCallback(async () => {
    if (!isAuthenticated) return null;
    return getAccessTokenSilently({
      authorizationParams: {
        audience: authConfig.audience,
        scope: authConfig.scope,
      },
    });
  }, [getAccessTokenSilently, isAuthenticated]);

  useEffect(() => {
    let cancelled = false;
    if (!isAuthenticated) {
      setPermissions([]);
      setPermissionsLoaded(false);
      setTokenError(null);
      return;
    }
    setPermissionsLoaded(false);
    getAccessToken()
      .then((token) => {
        if (cancelled) return;
        if (!token) {
          setPermissions([]);
          setPermissionsLoaded(true);
          return;
        }
        setPermissions(permissionsFromClaims(parseJwtClaims(token)));
        setPermissionsLoaded(true);
        setTokenError(null);
      })
      .catch((err) => {
        if (cancelled) return;
        setPermissions([]);
        setPermissionsLoaded(true);
        setTokenError(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [getAccessToken, isAuthenticated]);

  const hasPermission = useCallback(
    (permission: string) =>
      permissions.includes(permission) || permissions.includes(AUTH_PERMISSIONS.admin),
    [permissions],
  );

  const value = useMemo<AppAuthContext>(
    () => ({
      enabled: true,
      configured: true,
      isLoading: isLoading || (isAuthenticated && !permissionsLoaded),
      isAuthenticated,
      user,
      permissions,
      error: error?.message || tokenError,
      login: () =>
        loginWithRedirect({
          authorizationParams: {
            audience: authConfig.audience,
            scope: authConfig.scope,
            redirect_uri: window.location.origin,
          },
        }),
      logout: () => logout({ logoutParams: { returnTo: window.location.origin } }),
      getAccessToken,
      hasPermission,
    }),
    [
      error?.message,
      getAccessToken,
      hasPermission,
      isAuthenticated,
      isLoading,
      loginWithRedirect,
      logout,
      permissions,
      permissionsLoaded,
      tokenError,
      user,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function AppAuthProvider({ children }: { children: ReactNode }) {
  if (!authConfig.enabled) {
    return <StaticAuthProvider>{children}</StaticAuthProvider>;
  }
  if (!authConfig.configured) {
    return (
      <StaticAuthProvider configError="Auth0 is enabled but VITE_AUTH0_DOMAIN, VITE_AUTH0_CLIENT_ID, or VITE_AUTH0_AUDIENCE is missing.">
        {children}
      </StaticAuthProvider>
    );
  }
  return (
    <Auth0Provider
      domain={authConfig.domain}
      clientId={authConfig.clientId}
      authorizationParams={{
        audience: authConfig.audience,
        scope: authConfig.scope,
        redirect_uri: window.location.origin,
      }}
    >
      <AuthBridge>{children}</AuthBridge>
    </Auth0Provider>
  );
}

export function useAppAuth() {
  return useContext(AuthContext);
}
