import clsx from "clsx";

const variants = {
  green: "bg-emerald-50 text-emerald-700",
  yellow: "bg-accent-50 text-accent-700",
  red: "bg-red-50 text-red-700",
  gray: "bg-navy-100 text-navy-600",
  blue: "bg-blue-50 text-blue-700",
  teal: "bg-primary-50 text-primary-700",
  purple: "bg-purple-50 text-purple-700",
  amber: "bg-accent-50 text-accent-700",
};

const dotColors = {
  green: "bg-emerald-500",
  yellow: "bg-amber-500",
  red: "bg-red-500",
  gray: "bg-navy-400",
  blue: "bg-blue-500",
  teal: "bg-primary-500",
  purple: "bg-purple-500",
  amber: "bg-amber-500",
};

export default function Badge({ children, variant = "gray", dot = true, className }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold",
        variants[variant],
        className
      )}
    >
      {dot && <span className={clsx("w-1.5 h-1.5 rounded-full flex-shrink-0", dotColors[variant])} />}
      {children}
    </span>
  );
}
