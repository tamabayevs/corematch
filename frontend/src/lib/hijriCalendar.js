/**
 * Hijri Calendar Utility
 * Uses the browser's Intl.DateTimeFormat with the Islamic (Umm al-Qura) calendar
 * for accurate Gregorian-to-Hijri conversion used in Saudi Arabia.
 */

/**
 * Convert a Date object to a Hijri date string.
 * @param {Date|string} date - Gregorian date
 * @param {string} locale - Locale for formatting (default: "ar-SA")
 * @returns {string} Hijri formatted date
 */
export function toHijri(date, locale = "ar-SA") {
  const d = date instanceof Date ? date : new Date(date);
  if (isNaN(d.getTime())) return "";

  try {
    return new Intl.DateTimeFormat(locale, {
      calendar: "islamic-umalqura",
      year: "numeric",
      month: "long",
      day: "numeric",
    }).format(d);
  } catch {
    // Fallback if Intl API doesn't support the calendar
    return "";
  }
}

/**
 * Get Hijri date parts (year, month, day) from a Gregorian date.
 * @param {Date|string} date - Gregorian date
 * @returns {{ year: number, month: number, day: number } | null}
 */
export function getHijriParts(date) {
  const d = date instanceof Date ? date : new Date(date);
  if (isNaN(d.getTime())) return null;

  try {
    const formatter = new Intl.DateTimeFormat("en-US-u-ca-islamic-umalqura", {
      year: "numeric",
      month: "numeric",
      day: "numeric",
    });
    const parts = formatter.formatToParts(d);
    const result = {};
    for (const part of parts) {
      if (part.type === "year") result.year = parseInt(part.value, 10);
      if (part.type === "month") result.month = parseInt(part.value, 10);
      if (part.type === "day") result.day = parseInt(part.value, 10);
    }
    return result.year ? result : null;
  } catch {
    return null;
  }
}

/**
 * Format a dual date string: "21 Feb 2026 / 23 Sha'ban 1447"
 * @param {Date|string} date - Gregorian date
 * @param {string} language - "en" or "ar"
 * @returns {string} Dual formatted date
 */
export function formatDualDate(date, language = "en") {
  const d = date instanceof Date ? date : new Date(date);
  if (isNaN(d.getTime())) return "";

  const gregorian = new Intl.DateTimeFormat(language === "ar" ? "ar-SA" : "en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(d);

  const hijri = toHijri(d, language === "ar" ? "ar-SA" : "en-US-u-ca-islamic-umalqura");

  if (!hijri) return gregorian;
  return `${gregorian} / ${hijri}`;
}

/**
 * Get the Hijri month name.
 * @param {number} month - Hijri month number (1-12)
 * @param {string} language - "en" or "ar"
 * @returns {string}
 */
export function getHijriMonthName(month, language = "en") {
  const enMonths = [
    "Muharram", "Safar", "Rabi' al-Awwal", "Rabi' al-Thani",
    "Jumada al-Ula", "Jumada al-Thani", "Rajab", "Sha'ban",
    "Ramadan", "Shawwal", "Dhu al-Qi'dah", "Dhu al-Hijjah",
  ];
  const arMonths = [
    "محرم", "صفر", "ربيع الأول", "ربيع الثاني",
    "جمادى الأولى", "جمادى الآخرة", "رجب", "شعبان",
    "رمضان", "شوال", "ذو القعدة", "ذو الحجة",
  ];
  const months = language === "ar" ? arMonths : enMonths;
  return months[month - 1] || "";
}

/**
 * Format a short Hijri date (for compact display).
 * @param {Date|string} date - Gregorian date
 * @returns {string} Short Hijri date (e.g., "23/8/1447")
 */
export function toHijriShort(date) {
  const parts = getHijriParts(date);
  if (!parts) return "";
  return `${parts.day}/${parts.month}/${parts.year}`;
}

export default {
  toHijri,
  getHijriParts,
  formatDualDate,
  getHijriMonthName,
  toHijriShort,
};
