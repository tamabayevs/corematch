import clsx from "clsx";

export default function Card({ children, className, ...props }) {
  return (
    <div
      className={clsx(
        "bg-white rounded-xl border border-navy-200 p-6",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
