import clsx from "clsx";

const variants = {
  green: "bg-emerald-100 text-emerald-800",
  yellow: "bg-accent-100 text-accent-800",
  red: "bg-red-100 text-red-800",
  gray: "bg-navy-100 text-navy-600",
  blue: "bg-blue-100 text-blue-800",
  teal: "bg-primary-100 text-primary-800",
  purple: "bg-purple-100 text-purple-800",
  amber: "bg-accent-100 text-accent-800",
};

export default function Badge({ children, variant = "gray", className }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold",
        variants[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
