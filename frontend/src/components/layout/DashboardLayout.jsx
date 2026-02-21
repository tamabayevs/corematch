import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useI18n } from "../../lib/i18n";
import { useAuthStore } from "../../store/authStore";
import LanguageToggle from "../ui/LanguageToggle";
import clsx from "clsx";

/*
 * Sidebar structure (per Phase 1 plan):
 *
 * OVERVIEW
 *   Dashboard
 *   Campaigns        (dedicated list — uses same DashboardPage for now)
 *
 * REVIEW
 *   Video Reviews    (with badge count)
 *   Insights
 *
 * MANAGE
 *   Templates
 *
 * SETTINGS
 *   Settings
 *   PDPL Compliance
 */

const navSections = [
  {
    label: "nav.overview",
    items: [
      { path: "/dashboard", label: "nav.dashboard", icon: DashboardIcon, end: true },
    ],
  },
  {
    label: "nav.review",
    items: [
      { path: "/dashboard/reviews", label: "review.queue", icon: ReviewsIcon },
      { path: "/dashboard/insights", label: "nav.insights", icon: InsightsIcon },
    ],
  },
  {
    label: "nav.manage",
    items: [
      { path: "/dashboard/templates", label: "template.library", icon: TemplatesIcon },
    ],
  },
  {
    label: "nav.settings",
    items: [
      { path: "/dashboard/settings", label: "nav.settings", icon: SettingsIcon },
      { path: "/dashboard/compliance", label: "nav.compliance", icon: ComplianceIcon },
    ],
  },
];

export default function DashboardLayout() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-navy-50 flex">
      {/* Dark Navy Sidebar */}
      <aside className="w-64 bg-navy-900 flex flex-col fixed inset-y-0 start-0 z-30">
        {/* Logo */}
        <div className="p-6 pb-5">
          <h1 className="text-xl font-bold text-primary-100 tracking-tight">CoreMatch</h1>
          <p className="text-[11px] text-primary-400 font-medium tracking-wide mt-0.5">
            {t("brand.tagline")}
          </p>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 space-y-1 sidebar-scroll overflow-y-auto">
          {navSections.map((section) => (
            <div key={section.label}>
              <p className="px-3 pt-4 pb-1.5 text-[10px] font-semibold uppercase tracking-widest text-navy-500">
                {t(section.label)}
              </p>
              {section.items.map((item) => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  end={item.end}
                  className={({ isActive }) =>
                    clsx(
                      "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
                      isActive
                        ? "bg-gradient-to-r from-primary-600 to-primary-700 text-primary-50 shadow-md shadow-primary-900/20"
                        : "text-navy-400 hover:bg-navy-800 hover:text-navy-200"
                    )
                  }
                >
                  <item.icon className="w-5 h-5" />
                  {t(item.label)}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-navy-800 space-y-3">
          <LanguageToggle dark />

          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-600 text-navy-900 rounded-full flex items-center justify-center text-sm font-bold">
              {user?.full_name?.[0]?.toUpperCase() || "U"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-navy-200 truncate">
                {user?.full_name}
              </p>
              <p className="text-xs text-navy-500 truncate">{user?.email}</p>
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="w-full text-start text-sm text-navy-400 hover:text-navy-200 px-3 py-1.5 rounded-lg hover:bg-navy-800 transition-colors"
          >
            {t("auth.logout")}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 ms-64">
        <div className="max-w-6xl mx-auto px-8 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

// ── Icon Components ──────────────────────────────────────────

function DashboardIcon({ className }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
    </svg>
  );
}

function ReviewsIcon({ className }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
    </svg>
  );
}

function InsightsIcon({ className }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
    </svg>
  );
}

function TemplatesIcon({ className }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" />
    </svg>
  );
}

function SettingsIcon({ className }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  );
}

function ComplianceIcon({ className }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
    </svg>
  );
}
