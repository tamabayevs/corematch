/**
 * CoreMatch — Shared Date Formatting Utility
 * Wraps hijriCalendar.js for locale-aware dual Gregorian/Hijri display.
 *
 * Usage:
 *   import { formatDate, formatDateTime, formatRelativeTime } from "../lib/formatDate";
 *   const { locale } = useI18n();
 *   formatDate(isoString, locale);              // "Feb 21, 2026" or "٢١ فبراير ٢٠٢٦ / ٢٣ شعبان ١٤٤٧"
 *   formatDateTime(isoString, locale);           // includes time
 *   formatRelativeTime(isoString, locale);       // "5m ago" / "٥ دقائق"
 *   formatDate(isoString, locale, { style: "monthOnly" });  // "Feb" or Hijri month
 */

import { formatDualDate, getHijriParts, getHijriMonthName } from "./hijriCalendar";

/**
 * Format a date string with locale-awareness.
 * @param {string|Date} isoString - ISO date string or Date object
 * @param {string} locale - "en" or "ar"
 * @param {{ style?: "medium"|"short"|"datetime"|"monthOnly"|"relative" }} options
 * @returns {string}
 */
export function formatDate(isoString, locale = "en", options = {}) {
  if (!isoString) return "";
  const style = options.style || "medium";

  if (style === "relative") {
    return formatRelativeTime(isoString, locale);
  }

  const d = isoString instanceof Date ? isoString : new Date(isoString);
  if (isNaN(d.getTime())) return "";

  // Month-only style (for chart labels)
  if (style === "monthOnly") {
    if (locale === "ar") {
      const parts = getHijriParts(d);
      if (parts) return getHijriMonthName(parts.month, "ar");
    }
    return d.toLocaleDateString("en-US", { month: "short" });
  }

  // For Arabic locale: dual Gregorian/Hijri
  if (locale === "ar") {
    if (style === "datetime") {
      const dual = formatDualDate(d, "ar");
      const time = d.toLocaleTimeString("ar-SA", { hour: "2-digit", minute: "2-digit" });
      return `${dual} ${time}`;
    }
    return formatDualDate(d, "ar");
  }

  // English locale: standard Gregorian
  if (style === "datetime") {
    return d.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  if (style === "short") {
    return d.toLocaleDateString("en-US");
  }

  // Default: medium
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/**
 * Format a date with time included.
 */
export function formatDateTime(isoString, locale = "en") {
  return formatDate(isoString, locale, { style: "datetime" });
}

/**
 * Format a relative time string ("5m ago", "2d ago").
 * Falls back to medium format for dates older than 7 days.
 */
export function formatRelativeTime(isoString, locale = "en") {
  if (!isoString) return "";
  const d = isoString instanceof Date ? isoString : new Date(isoString);
  if (isNaN(d.getTime())) return "";

  const now = new Date();
  const diffMs = now - d;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (locale === "ar") {
    if (diffMins < 1) return "الآن";
    if (diffMins < 60) return `منذ ${diffMins} د`;
    if (diffHours < 24) return `منذ ${diffHours} س`;
    if (diffDays < 7) return `منذ ${diffDays} ي`;
    return formatDate(isoString, locale);
  }

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return formatDate(isoString, locale);
}

export default { formatDate, formatDateTime, formatRelativeTime };
