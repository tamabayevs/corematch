import { useI18n } from "../../lib/i18n";
import clsx from "clsx";

export default function LanguageToggle({ className, dark = false }) {
  const { locale, setLocale } = useI18n();

  return (
    <div className={clsx("flex items-center gap-1 text-sm", className)}>
      <button
        onClick={() => setLocale("en")}
        className={clsx(
          "px-2.5 py-1 rounded-md transition-colors font-medium",
          locale === "en"
            ? dark
              ? "bg-primary-600 text-white"
              : "bg-primary-100 text-primary-700"
            : dark
              ? "text-navy-400 hover:text-navy-200"
              : "text-navy-400 hover:text-navy-600"
        )}
      >
        EN
      </button>
      <span className={dark ? "text-navy-700" : "text-navy-300"}>|</span>
      <button
        onClick={() => setLocale("ar")}
        className={clsx(
          "px-2.5 py-1 rounded-md transition-colors font-medium font-cairo",
          locale === "ar"
            ? dark
              ? "bg-primary-600 text-white"
              : "bg-primary-100 text-primary-700"
            : dark
              ? "text-navy-400 hover:text-navy-200"
              : "text-navy-400 hover:text-navy-600"
        )}
      >
        عربي
      </button>
    </div>
  );
}
