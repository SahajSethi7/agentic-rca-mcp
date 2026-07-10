import * as SwitchPrimitive from "@radix-ui/react-switch";

export default function Switch({
  checked,
  onCheckedChange,
  id,
  "aria-label": ariaLabel,
  "aria-labelledby": ariaLabelledBy,
}: {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  id?: string;
  "aria-label"?: string;
  "aria-labelledby"?: string;
}) {
  return (
    <SwitchPrimitive.Root
      id={id}
      checked={checked}
      onCheckedChange={onCheckedChange}
      aria-label={ariaLabel}
      aria-labelledby={ariaLabelledBy}
      className="relative h-6 w-11 flex-shrink-0 rounded-full bg-slate-300 outline-none transition-colors duration-200 focus-visible:ring-[3px] focus-visible:ring-primary focus-visible:ring-offset-2 data-[state=checked]:bg-primary-hover"
    >
      <SwitchPrimitive.Thumb className="block h-4 w-4 translate-x-1 rounded-full bg-white shadow transition-transform duration-200 ease-out data-[state=checked]:translate-x-6" />
    </SwitchPrimitive.Root>
  );
}
