import clsx from "clsx";

export default function Input({
  label,
  error,
  id,
  type = "text",
  className,
  ...props
}) {
  return (
    <div className={className}>
      {label && (
        <label htmlFor={id} className="block text-sm font-medium text-navy-700 mb-1">
          {label}
        </label>
      )}
      <input
        id={id}
        type={type}
        className={clsx(
          "block w-full rounded-lg border px-3 py-2 text-sm",
          "focus:outline-none focus:ring-2 focus:ring-offset-0",
          "placeholder:text-navy-400",
          error
            ? "border-red-300 focus:border-red-500 focus:ring-red-500"
            : "border-navy-300 focus:border-primary-500 focus:ring-primary-500"
        )}
        {...props}
      />
      {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
    </div>
  );
}
