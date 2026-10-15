import { Container } from "@cloudflare/containers";

/**
 * Every setting the Django container needs. Each name must exist exactly once, either as a
 * secret (`wrangler secret bulk`, the default) or, for a value that is empty by design, as an
 * empty entry under "vars" in wrangler.jsonc (Cloudflare does not accept empty secrets).
 */
const SETTINGS = [
	"PROJECT_MANAGEMENT_SECRET_KEY",
	"PROJECT_MANAGEMENT_DB_PASSWORD",
	"PROJECT_MANAGEMENT_REDIS_URL",
	"PROJECT_MANAGEMENT_R2_ACCESS_KEY_ID",
	"PROJECT_MANAGEMENT_R2_SECRET_ACCESS_KEY",
	"PROJECT_MANAGEMENT_INTEGRATION_ENCRYPTION_KEYS",
	"PROJECT_MANAGEMENT_DEBUG",
	"PROJECT_MANAGEMENT_ENVIRONMENT",
	"PROJECT_MANAGEMENT_USE_SQLITE",
	"PROJECT_MANAGEMENT_RELAX_THROTTLES",
	"PROJECT_MANAGEMENT_SECURE_COOKIES",
	"PROJECT_MANAGEMENT_SSL_REDIRECT",
	"PROJECT_MANAGEMENT_NUM_PROXIES",
	"PROJECT_MANAGEMENT_COOKIE_DOMAIN",
	"PROJECT_MANAGEMENT_ALLOWED_HOSTS",
	"PROJECT_MANAGEMENT_FRONTEND_URL",
	"PROJECT_MANAGEMENT_CORS_ALLOWED_ORIGINS",
	"PROJECT_MANAGEMENT_CSRF_TRUSTED_ORIGINS",
	"PROJECT_MANAGEMENT_PUBLIC_API_URL",
	"PROJECT_MANAGEMENT_DB_HOST",
	"PROJECT_MANAGEMENT_DB_PORT",
	"PROJECT_MANAGEMENT_DB_NAME",
	"PROJECT_MANAGEMENT_DB_USER",
	"PROJECT_MANAGEMENT_DB_SSLMODE",
	"PROJECT_MANAGEMENT_EMAIL_BACKEND",
	"PROJECT_MANAGEMENT_DEFAULT_FROM_EMAIL",
	"PROJECT_MANAGEMENT_EMAIL_HOST",
	"PROJECT_MANAGEMENT_EMAIL_PORT",
	"PROJECT_MANAGEMENT_EMAIL_HOST_USER",
	"PROJECT_MANAGEMENT_EMAIL_HOST_PASSWORD",
	"PROJECT_MANAGEMENT_EMAIL_USE_TLS",
	"PROJECT_MANAGEMENT_GOOGLE_CLIENT_ID",
	"PROJECT_MANAGEMENT_SENTRY_DSN",
	"PROJECT_MANAGEMENT_SLACK_CLIENT_ID",
	"PROJECT_MANAGEMENT_SLACK_CLIENT_SECRET",
	"PROJECT_MANAGEMENT_SLACK_SIGNING_SECRET",
	"PROJECT_MANAGEMENT_R2_ENDPOINT_URL",
	"PROJECT_MANAGEMENT_R2_BUCKET_NAME",
	"PROJECT_MANAGEMENT_R2_PUBLIC_BASE_URL",
] as const;

type SettingName = (typeof SETTINGS)[number];

interface Env extends Record<SettingName, string> {
	BACKEND: DurableObjectNamespace<BackendContainer>;
}

/** Values left over from secrets.example.json: they mean "someone forgot to fill this in". */
const PLACEHOLDERS = ["FILL_ME", "SUBDOMAIN"];

/**
 * Same rule as settings.py: a missing variable is an error, an empty one is fine. A value
 * that still holds a placeholder is an error too; the message names the variables, never
 * their values.
 */
function containerEnv(env: Env): Record<string, string> {
	const result: Record<string, string> = {};
	const missing: string[] = [];
	const placeholders: string[] = [];
	for (const name of SETTINGS) {
		const value = env[name];
		if (value === undefined) {
			missing.push(name);
			continue;
		}
		if (PLACEHOLDERS.some((placeholder) => value.includes(placeholder))) {
			placeholders.push(name);
		}
		result[name] = value;
	}
	if (missing.length > 0) {
		throw new SettingsError(`Missing environment variable(s): ${missing.join(", ")}`);
	}
	if (placeholders.length > 0) {
		throw new SettingsError(`Placeholder value left in: ${placeholders.join(", ")}`);
	}
	return result;
}

class SettingsError extends Error {}

/** The Django container. It sleeps when idle and starts again on the next request. */
export class BackendContainer extends Container<Env> {
	defaultPort = 8080;
	sleepAfter = "10m";

	/**
	 * Called by the Worker on every request with the settings it sees right now. A running
	 * container keeps the environment it started with, and this object can outlive a
	 * secret change, so compare a fingerprint of the settings with the one the container
	 * was started with and restart it when they differ. Only the hash is stored.
	 */
	async syncSettings(settings: Record<string, string>): Promise<void> {
		const fingerprint = await settingsFingerprint(settings);
		this.envVars = settings;
		if ((await this.ctx.storage.get<string>(FINGERPRINT_KEY)) !== fingerprint) {
			if (this.ctx.container?.running) await this.stop();
			await this.ctx.storage.put(FINGERPRINT_KEY, fingerprint);
		}
	}
}

const FINGERPRINT_KEY = "settings-fingerprint";

/** SHA-256 of the settings, so the values themselves are never stored. */
async function settingsFingerprint(settings: Record<string, string>): Promise<string> {
	const text = JSON.stringify(Object.entries(settings).sort(([a], [b]) => a.localeCompare(b)));
	const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
	return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

export default {
	async fetch(request: Request, env: Env): Promise<Response> {
		// Tell Django the original scheme and client address (it sees only this Worker)
		const headers = new Headers(request.headers);
		headers.set("X-Forwarded-Proto", "https");
		const clientIp = request.headers.get("CF-Connecting-IP");
		if (clientIp) headers.set("X-Forwarded-For", clientIp);

		const backend = env.BACKEND.getByName("backend");
		try {
			await backend.syncSettings(containerEnv(env));
		} catch (error) {
			if (error instanceof SettingsError) {
				return new Response(error.message, { status: 500 });
			}
			throw error;
		}
		return backend.fetch(new Request(request, { headers }));
	},
} satisfies ExportedHandler<Env>;
