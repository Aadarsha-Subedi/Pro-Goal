/// <reference types="vite/client" />

// Validated at startup by vite.config.ts: a missing variable stops dev and build.
interface ImportMetaEnv {
	/** API origin. Empty means same origin (dev proxy, nginx or the Worker forward /api). */
	readonly VITE_API_BASE: string;
	/** Google Identity Services client id. Empty disables the Google button. */
	readonly VITE_GOOGLE_CLIENT_ID: string;
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}
