import Button from "./Button";

export default function EmptyState({ icon, title, description, actionLabel, onAction }) {
  return (
    <div className="text-center py-12 px-4">
      {icon && <div className="mx-auto mb-4 text-navy-400">{icon}</div>}
      <h3 className="text-lg font-medium text-navy-900 mb-1">{title}</h3>
      {description && (
        <p className="text-sm text-navy-500 mb-6 max-w-sm mx-auto">{description}</p>
      )}
      {actionLabel && onAction && (
        <Button onClick={onAction}>{actionLabel}</Button>
      )}
    </div>
  );
}
