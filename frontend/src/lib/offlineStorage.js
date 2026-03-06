/**
 * CoreMatch — Offline Video Storage
 * Uses IndexedDB to store recorded video blobs when upload fails.
 * Auto-retries uploads when the user comes back online.
 */

const DB_NAME = "corematch-offline";
const DB_VERSION = 1;
const STORE_NAME = "pending-videos";

function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "id" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

/**
 * Save a video blob to IndexedDB for later upload.
 * @param {string} token - Interview invite token
 * @param {number} questionIndex - Question index
 * @param {Blob} blob - Recorded video blob
 * @param {string} questionText - Question text for reference
 */
export async function saveVideoBlob(token, questionIndex, blob, questionText = "") {
  try {
    const db = await openDB();
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    const id = `${token}_q${questionIndex}`;
    store.put({
      id,
      token,
      questionIndex,
      blob,
      questionText,
      savedAt: new Date().toISOString(),
    });
    await new Promise((resolve, reject) => {
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
    return true;
  } catch (err) {
    console.error("Failed to save video to IndexedDB:", err);
    return false;
  }
}

/**
 * Get all pending (unuploaded) video blobs for a given token.
 * @param {string} token - Interview invite token
 * @returns {Array} - Array of { id, token, questionIndex, blob, savedAt }
 */
export async function getPendingUploads(token) {
  try {
    const db = await openDB();
    const tx = db.transaction(STORE_NAME, "readonly");
    const store = tx.objectStore(STORE_NAME);
    const all = await new Promise((resolve, reject) => {
      const req = store.getAll();
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
    return token ? all.filter((item) => item.token === token) : all;
  } catch (err) {
    console.error("Failed to get pending uploads:", err);
    return [];
  }
}

/**
 * Remove a successfully uploaded video from IndexedDB.
 * @param {string} token - Interview invite token
 * @param {number} questionIndex - Question index
 */
export async function clearPendingUpload(token, questionIndex) {
  try {
    const db = await openDB();
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    const id = `${token}_q${questionIndex}`;
    store.delete(id);
    await new Promise((resolve, reject) => {
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
    return true;
  } catch (err) {
    console.error("Failed to clear pending upload:", err);
    return false;
  }
}

/**
 * Get the count of all pending uploads across all tokens.
 */
export async function getPendingCount() {
  try {
    const db = await openDB();
    const tx = db.transaction(STORE_NAME, "readonly");
    const store = tx.objectStore(STORE_NAME);
    return new Promise((resolve, reject) => {
      const req = store.count();
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  } catch {
    return 0;
  }
}
