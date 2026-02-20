import { useI18n } from "../../lib/i18n";
import clsx from "clsx";

export default function LanguageToggle({ className }) {
  const { locale, setLocale } = useI18n();

  return (
    <div className={clsx("flex items-center gap-1 text-sm", className)}>
      <button
        onClick={() => setLocale("en")}
        className={clsx(
          "px-2 py-1 rounded transition-colors",
          locale === "en"
            ? "bg-primary-100 text-primary-700 font-medium"
            : "text-gray-500 hover:text-gray-700"
        )}
      >
        EN
      </button>
      <span className="text-gray-300">|</span>
      <button
        onClick={() => setLocale("ar")}
        className={clsx(
          "px-2 py-1 rounded transition-colors font-cairo",
          locale === "ar"
            ? "bg-primary-100 text-primary-700 font-medium"
            : "text-gray-500 hover:text-gray-700"
        )}
      >
        عربي
      </button>
    </div>
  );
}
