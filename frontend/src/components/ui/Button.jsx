import clsx from "clsx";

const variants = {
  primary:
    "bg-primary-600 text-white hover:bg-primary-700 focus:ring-primary-500 shadow-sm",
  secondary:
    "bg-white text-navy-700 border border-navy-200 hover:bg-navy-50 focus:ring-primary-500",
  danger:
    "bg-red-600 text-white hover:bg-red-700 focus:ring-red-500",
  ghost:
    "bg-transparent text-navy-500 hover:bg-navy-100 hover:text-navy-700 focus:ring-navy-500",
  success:
    "bg-emerald-600 text-white hover:bg-emerald-700 focus:ring-emerald-500",
  warning:
    "bg-accent-500 text-white hover:bg-accent-600 focus:ring-accent-500",
  accent:
    "bg-accent-500 text-white hover:bg-accent-600 focus:ring-accent-500 shadow-sm",
};

const sizes = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2 text-sm",
  lg: "px-6 py-3 text-base",
};

export default function Button({
  children,
  variant = "primary",
  size = "md",
  loading = false,
  disabled = false,
  className,
  ...props
}) {
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center font-medium rounded-lg",
        "focus:outline-none focus:ring-2 focus:ring-offset-2",
        "transition-all duration-150",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        variants[variant],
        sizes[size],
        className
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <svg
          className="animate-spin -ms-1 me-2 h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
      )}
      {children}
    </button>
  );
}
