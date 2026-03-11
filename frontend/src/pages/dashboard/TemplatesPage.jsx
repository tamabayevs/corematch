import { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useI18n } from "../../lib/i18n";
import { templatesApi } from "../../api/templates";
import Card from "../../components/ui/Card";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Spinner from "../../components/ui/Spinner";
import EmptyState from "../../components/ui/EmptyState";

/** Category order for display */
const CATEGORY_ORDER = [
  "Hospitality & Tourism",
  "Retail",
  "Logistics & Supply Chain",
  "Construction & Facilities",
  "Healthcare",
  "Technology & IT",
  "Digital & Marketing",
  "Finance & Banking",
  "Administrative & Office",
  "Call Center & Support",
  "Education",
  "Oil & Gas / Energy",
  "Security",
  "Management",
  "General",
];

export default function TemplatesPage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleteLoading, setDeleteLoading] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    setLoading(true);
    try {
      const res = await templatesApi.list();
      setTemplates(res.data.templates || []);
    } catch {
      // Handle silently
    } finally {
      setLoading(false);
    }
  };

  // Derive categories from templates
  const categories = useMemo(() => {
    const cats = new Set();
    templates.forEach((t) => {
      if (t.category) cats.add(t.category);
    });
    // Sort by predefined order, unknowns at end
    return [...cats].sort((a, b) => {
      const ia = CATEGORY_ORDER.indexOf(a);
      const ib = CATEGORY_ORDER.indexOf(b);
      return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
    });
  }, [templates]);

  // Filter templates
  const filtered = useMemo(() => {
    let result = templates;
    if (selectedCategory !== "all") {
      if (selectedCategory === "custom") {
        result = result.filter((t) => !t.is_system);
      } else if (selectedCategory === "uncategorized") {
        result = result.filter((t) => t.is_system && !t.category);
      } else {
        result = result.filter((t) => t.category === selectedCategory);
      }
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (t) =>
          t.name.toLowerCase().includes(q) ||
          (t.description || "").toLowerCase().includes(q) ||
          (t.category || "").toLowerCase().includes(q)
      );
    }
    return result;
  }, [templates, selectedCategory, searchQuery]);

  // Group filtered templates by category for display
  const grouped = useMemo(() => {
    const groups = {};
    filtered.forEach((t) => {
      const cat = t.category || (t.is_system ? "General" : "My Templates");
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(t);
    });
    // Sort groups by predefined order
    return Object.entries(groups).sort(([a], [b]) => {
      if (a === "My Templates") return -1;
      if (b === "My Templates") return 1;
      const ia = CATEGORY_ORDER.indexOf(a);
      const ib = CATEGORY_ORDER.indexOf(b);
      return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
    });
  }, [filtered]);

  const handleDelete = async (templateId, templateName) => {
    if (!window.confirm(t("template.deleteConfirm", { name: templateName }))) {
      return;
    }
    setDeleteLoading(templateId);
    try {
      await templatesApi.delete(templateId);
      setTemplates((prev) => prev.filter((tpl) => tpl.id !== templateId));
    } catch {
      // Handle silently
    } finally {
      setDeleteLoading(null);
    }
  };

  const handleUseTemplate = (templateId) => {
    navigate(`/dashboard/campaigns/new?template=${templateId}`);
  };

  const systemCount = templates.filter((t) => t.is_system).length;
  const customCount = templates.filter((t) => !t.is_system).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-navy-500">
            {systemCount} industry templates • {customCount} custom
          </p>
        </div>
        <Button onClick={() => navigate("/dashboard/templates/new")}>
          {t("template.createTemplate")}
        </Button>
      </div>

      {/* Search + Category Filter Bar */}
      {!loading && templates.length > 0 && (
        <div className="space-y-3">
          {/* Search */}
          <div className="relative">
            <svg
              className="absolute start-3 top-1/2 -translate-y-1/2 w-4 h-4 text-navy-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t("template.searchPlaceholder") || "Search templates..."}
              className="w-full ps-9 pe-4 py-2 border border-navy-200 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
          </div>

          {/* Category pills */}
          <div className="flex flex-wrap gap-2">
            <CategoryPill
              label={`All (${templates.length})`}
              active={selectedCategory === "all"}
              onClick={() => setSelectedCategory("all")}
            />
            {customCount > 0 && (
              <CategoryPill
                label={`My Templates (${customCount})`}
                active={selectedCategory === "custom"}
                onClick={() => setSelectedCategory("custom")}
              />
            )}
            {categories.map((cat) => {
              const count = templates.filter((t) => t.category === cat).length;
              return (
                <CategoryPill
                  key={cat}
                  label={`${cat} (${count})`}
                  active={selectedCategory === cat}
                  onClick={() => setSelectedCategory(cat)}
                />
              );
            })}
          </div>
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : templates.length === 0 ? (
        <EmptyState
          icon={
            <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
              />
            </svg>
          }
          title={t("template.noTemplates")}
          description={t("template.noTemplatesDesc")}
          actionLabel={t("template.createTemplate")}
          onAction={() => navigate("/dashboard/templates/new")}
        />
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-navy-500">
          <p className="text-lg font-medium">No templates match your search</p>
          <p className="text-sm mt-1">Try a different search term or category</p>
        </div>
      ) : (
        <div className="space-y-8">
          {grouped.map(([category, items]) => (
            <div key={category}>
              <h2 className="text-lg font-semibold text-navy-800 mb-3 flex items-center gap-2">
                <CategoryIcon category={category} />
                {category}
                <span className="text-sm font-normal text-navy-400">({items.length})</span>
              </h2>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {items.map((template) => (
                  <TemplateCard
                    key={template.id}
                    template={template}
                    onUse={handleUseTemplate}
                    onEdit={(id) => navigate(`/dashboard/templates/${id}/edit`)}
                    onDelete={handleDelete}
                    deleteLoading={deleteLoading}
                    t={t}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Sub-components ────────────────────────────────────────────

function CategoryPill({ label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors whitespace-nowrap ${
        active
          ? "bg-primary-600 text-white shadow-sm"
          : "bg-navy-100 text-navy-600 hover:bg-navy-200"
      }`}
    >
      {label}
    </button>
  );
}

/** Simple category icon mapping */
function CategoryIcon({ category }) {
  const icons = {
    "Hospitality & Tourism": "🏨",
    "Retail": "🛍️",
    "Logistics & Supply Chain": "🚚",
    "Construction & Facilities": "🏗️",
    "Healthcare": "🏥",
    "Technology & IT": "💻",
    "Digital & Marketing": "📱",
    "Finance & Banking": "🏦",
    "Administrative & Office": "📋",
    "Call Center & Support": "📞",
    "Education": "🎓",
    "Oil & Gas / Energy": "⚡",
    "Security": "🛡️",
    "Management": "📊",
    "General": "📝",
    "My Templates": "⭐",
  };
  return <span>{icons[category] || "📁"}</span>;
}

function TemplateCard({ template, onUse, onEdit, onDelete, deleteLoading, t }) {
  const isSystem = template.is_system;
  const questionCount = template.questions?.length || template.question_count || 0;

  return (
    <Card className="flex flex-col justify-between hover:border-primary-300 hover:shadow-md transition-all">
      <div>
        {/* Header row: badge */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-navy-900 truncate text-sm">{template.name}</h3>
          </div>
          {isSystem ? (
            <Badge variant="blue">
              <svg
                className="w-3 h-3 me-1"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                />
              </svg>
              {t("template.system")}
            </Badge>
          ) : (
            <Badge variant="purple">{t("template.custom")}</Badge>
          )}
        </div>

        {/* Description */}
        {template.description && (
          <p className="text-xs text-navy-500 mb-3 line-clamp-2">{template.description}</p>
        )}

        {/* Meta info */}
        <div className="flex items-center gap-3 text-xs text-navy-400">
          <span className="flex items-center gap-1">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            {questionCount === 1 ? `1 question` : t("template.questions", { count: questionCount })}
          </span>
          {template.language && (
            <span className="flex items-center gap-1">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129"
                />
              </svg>
              {template.language === "ar" ? "Arabic" : "English"}
            </span>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 mt-4 pt-4 border-t border-navy-100">
        <Button size="sm" onClick={() => onUse(template.id)} className="flex-1">
          {t("template.useTemplate")}
        </Button>
        {!isSystem && (
          <>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onEdit(template.id)}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                />
              </svg>
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onDelete(template.id, template.name)}
              loading={deleteLoading === template.id}
              className="text-red-500 hover:text-red-700 hover:bg-red-50"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
            </Button>
          </>
        )}
      </div>
    </Card>
  );
}
