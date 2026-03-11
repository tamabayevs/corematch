import clsx from "clsx";

export default function Card({ children, className, hoverable = false, ...props }) {
  return (
    <div
      className={clsx(
        "bg-white rounded-xl border border-navy-200 p-5 transition-all",
        hoverable && "hover:border-navy-300 hover:shadow-card-hover cursor-pointer",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
