const PREFIX = "tk:v2:";

export function read(key, fallback) {
  try { return JSON.parse(localStorage.getItem(PREFIX + key)) ?? fallback; }
  catch { return fallback; }
}

export function write(key, value) {
  localStorage.setItem(PREFIX + key, JSON.stringify(value));
}

export function remove(key) {
  localStorage.removeItem(PREFIX + key);
}
