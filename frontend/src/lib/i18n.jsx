import { createContext, useContext, useState, useCallback, useEffect } from "react";
import en from "./translations/en.json";
import ar from "./translations/ar.json";

const translations = { en, ar };

const I18nContext = createContext(null);

export function I18nProvider({ children }) {
  const [locale, setLocaleState] = useState(() => {
    return localStorage.getItem("corematch_locale") || "en";
  });

  const dir = locale === "ar" ? "rtl" : "ltr";

  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dir = dir;
  }, [locale, dir]);

  const setLocale = useCallback((newLocale) => {
    setLocaleState(newLocale);
    localStorage.setItem("corematch_locale", newLocale);
  }, []);

  const t = useCallback(
    (key, params) => {
      const keys = key.split(".");
      let value = translations[locale];
      for (const k of keys) {
        if (value == null) break;
        value = value[k];
      }
      if (typeof value !== "string") {
        // Fallback to English
        value = translations.en;
        for (const k of keys) {
          if (value == null) break;
          value = value[k];
        }
      }
      if (typeof value !== "string") return key;

      // Replace {{param}} placeholders
      if (params) {
        return value.replace(/\{\{(\w+)\}\}/g, (_, name) =>
          params[name] !== undefined ? params[name] : `{{${name}}}`
        );
      }
      return value;
    },
    [locale]
  );

  return (
    <I18nContext.Provider value={{ locale, setLocale, dir, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}
