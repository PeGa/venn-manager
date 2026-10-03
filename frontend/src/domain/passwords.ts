/** Password rules mirrored from the API (BACKEND.md § 8.3). */

export const PASSWORD_MIN = 8;
export const PASSWORD_MAX = 128;

/** What is wrong with a new password and its repetition, if anything. */
export function passwordProblem(password: string, repeat: string): "length" | "mismatch" | null {
  if (password.length < PASSWORD_MIN || password.length > PASSWORD_MAX) {
    return "length";
  }
  return password === repeat ? null : "mismatch";
}
