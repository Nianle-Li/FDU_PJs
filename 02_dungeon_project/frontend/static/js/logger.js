// Simple logger with global debug switch
export const DEBUG = false; // set to true to enable console logging during development

export function log(...args) {
  if (DEBUG) console.log(...args);
}
export function info(...args) {
  if (DEBUG) console.info(...args);
}
export function warn(...args) {
  if (DEBUG) console.warn(...args);
}
export function debug(...args) {
  if (DEBUG) console.debug(...args);
}
export function error(...args) {
  // always show errors to help diagnose issues
  console.error(...args);
}
