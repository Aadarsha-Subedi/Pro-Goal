import path from 'node:path';
import tailwindcss from '@tailwindcss/vite';
import { tanstackRouter } from '@tanstack/router-plugin/vite';
import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

/** Return a required env var; fail loudly when it is not set (empty is allowed). */
function requireEnv(env: Record<string, string>, name: string): string {
	if (!(name in env)) {
		throw new Error(`Missing environment variable: ${name} (see .env.example)`);
	}
	return env[name];
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
	// Prefix '' also loads variables without VITE_; real environment variables win over .env.
	const env = loadEnv(mode, process.cwd(), '');
	requireEnv(env, 'VITE_API_BASE');
	requireEnv(env, 'VITE_GOOGLE_CLIENT_ID');

	return {
		plugins: [
			tanstackRouter({ target: 'react', autoCodeSplitting: true }),
			react(),
			tailwindcss(),
		],
		resolve: {
			alias: { '@': path.resolve(import.meta.dirname, './src') },
		},
		server: {
			port: 3000,
			// Lets the dev server answer through an ngrok tunnel (needed to test Slack sign-in locally).
			allowedHosts: ['.ngrok-free.dev', '.ngrok-free.app', '.ngrok.app'],
			// The dev server forwards /api to the backend; builds and tests do not need it.
			proxy:
				mode === 'development'
					? {
							'/api': {
								target: requireEnv(env, 'DEV_API_PROXY_TARGET'),
								// Keep the browser's Host header: Django only allows localhost
								changeOrigin: false,
							},
						}
					: undefined,
		},
	};
});
