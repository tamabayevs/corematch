import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useI18n } from "../../lib/i18n";
import { useAuthStore } from "../../store/authStore";
import LanguageToggle from "../ui/LanguageToggle";
import clsx from "clsx";

const navItems = [
  { path: "/dashboard", label: "nav.dashboard", icon: DashboardIcon, end: true },
  { path: "/dashboard/settings", label: "nav.settings", icon: SettingsIcon },
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
          <p className="px-3 pt-2 pb-1.5 text-[10px] font-semibold uppercase tracking-widest text-navy-500">
            {t("nav.overview") || "Overview"}
          </p>
          {navItems.map((item) => (
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

function DashboardIcon({ className }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
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
