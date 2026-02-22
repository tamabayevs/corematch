import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useI18n } from "../../lib/i18n";
import { templatesApi } from "../../api/templates";
import Card from "../../components/ui/Card";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Spinner from "../../components/ui/Spinner";
import EmptyState from "../../components/ui/EmptyState";

export default function TemplatesPage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleteLoading, setDeleteLoading] = useState(null);

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-navy-900">{t("template.library")}</h1>
        </div>
        <Button onClick={() => navigate("/dashboard/templates/new")}>
          {t("template.createTemplate")}
        </Button>
      </div>

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
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {templates.map((template) => (
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
      )}
    </div>
  );
}

// ─── Sub-components ────────────────────────────────────────────

function TemplateCard({ template, onUse, onEdit, onDelete, deleteLoading, t }) {
  const isSystem = template.is_system;
  const questionCount = template.questions?.length || template.question_count || 0;

  return (
    <Card className="flex flex-col justify-between hover:border-primary-300 hover:shadow-md transition-all">
      <div>
        {/* Header row: badge */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-navy-900 truncate">{template.name}</h3>
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
          <p className="text-sm text-navy-500 mb-3 line-clamp-2">{template.description}</p>
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
