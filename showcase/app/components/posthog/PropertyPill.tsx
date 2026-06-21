import { cn } from "@/lib/utils";

export function PropertyPill({
  label,
  value,
  variant = "default",
  className,
}: {
  label: string;
  value: string;
  variant?: "default" | "green" | "orange" | "blue" | "muted";
  className?: string;
}) {
  return (
    <span
      className={cn(
        "ph-tag",
        variant === "green" && "ph-tag-green",
        variant === "orange" && "ph-tag-orange",
        variant === "blue" && "ph-tag-blue",
        className,
      )}
    >
      <span style={{ opacity: 0.65 }}>{label}</span>
      {value}
    </span>
  );
}
