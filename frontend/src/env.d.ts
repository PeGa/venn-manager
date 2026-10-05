/** Build-time settings Vite substitutes into the bundle. */
interface ImportMetaEnv {
  /** Backend port on the page's host; unset means same origin (dev proxy). */
  readonly VITE_API_PORT?: string;
}
