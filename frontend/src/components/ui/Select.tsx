import {
  Children,
  isValidElement,
  type ChangeEvent,
  type FocusEventHandler,
  type ReactNode,
  type SelectHTMLAttributes,
} from "react";
import * as SelectPrimitive from "@radix-ui/react-select";
import { ChevronDownIcon } from "../icons";

const EMPTY_VALUE = "__empty_select_value__";

type OptionModel = {
  value: string;
  itemValue: string;
  label: ReactNode;
  disabled?: boolean;
};

function optionModels(children: ReactNode): OptionModel[] {
  return Children.toArray(children).flatMap((child) => {
    if (!isValidElement(child) || child.type !== "option") return [];
    const props = child.props as {
      value?: string | number;
      children?: ReactNode;
      disabled?: boolean;
    };
    const value = String(props.value ?? (typeof props.children === "string" ? props.children : ""));
    return [{
      value,
      itemValue: value === "" ? EMPTY_VALUE : value,
      label: props.children,
      disabled: props.disabled,
    }];
  });
}

export default function Select({
  className = "",
  children,
  value,
  defaultValue,
  disabled,
  id,
  name,
  onChange,
  onBlur,
  "aria-label": ariaLabel,
  "aria-labelledby": ariaLabelledBy,
  "aria-describedby": ariaDescribedBy,
}: SelectHTMLAttributes<HTMLSelectElement>) {
  const options = optionModels(children);
  const selectedValue = value == null ? undefined : String(value);
  const initialValue = defaultValue == null ? undefined : String(defaultValue);
  const placeholder = options.find((option) => option.value === "")?.label ?? "Select";

  function handleValueChange(nextItemValue: string) {
    const nextValue = nextItemValue === EMPTY_VALUE ? "" : nextItemValue;
    const event = {
      target: { value: nextValue, name },
      currentTarget: { value: nextValue, name },
    } as unknown as ChangeEvent<HTMLSelectElement>;
    onChange?.(event);
  }

  return (
    <SelectPrimitive.Root
      value={selectedValue}
      defaultValue={initialValue}
      disabled={disabled}
      onValueChange={handleValueChange}
    >
      {name && <input type="hidden" name={name} value={selectedValue ?? initialValue ?? ""} />}
      <SelectPrimitive.Trigger
        id={id}
        aria-label={ariaLabel}
        aria-labelledby={ariaLabelledBy}
        aria-describedby={ariaDescribedBy}
        onBlur={onBlur as unknown as FocusEventHandler<HTMLButtonElement>}
        className={`flex h-10 w-full min-w-0 cursor-pointer items-center justify-between gap-2 rounded-md border border-slate-300 bg-white pl-3 pr-2 text-left text-body-sm font-semibold text-ink outline-none transition hover:border-primary-soft focus:border-primary focus:ring-[3px] focus:ring-primary-tint data-[disabled]:cursor-not-allowed data-[placeholder]:text-ink-muted data-[disabled]:opacity-60 ${className}`}
      >
        <SelectPrimitive.Value placeholder={placeholder} />
        <SelectPrimitive.Icon asChild>
          <ChevronDownIcon className="h-4 w-4 flex-shrink-0 text-primary-selected" />
        </SelectPrimitive.Icon>
      </SelectPrimitive.Trigger>
      <SelectPrimitive.Portal>
        <SelectPrimitive.Content
          position="popper"
          sideOffset={6}
          className="z-50 max-h-[280px] min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-md border border-slate-200 bg-white shadow-hero"
        >
          <SelectPrimitive.Viewport className="p-1">
            {options.map((option) => (
              <SelectPrimitive.Item
                key={`${option.itemValue}-${String(option.label)}`}
                value={option.itemValue}
                disabled={option.disabled}
                className="relative flex min-h-9 cursor-pointer select-none items-center rounded-md py-2 pl-8 pr-3 text-body-sm font-semibold text-ink outline-none data-[disabled]:pointer-events-none data-[highlighted]:bg-primary-tint data-[highlighted]:text-primary-selected data-[disabled]:opacity-50"
              >
                <SelectPrimitive.ItemIndicator className="absolute left-2 grid h-4 w-4 place-items-center text-primary-selected">
                  <span className="h-1.5 w-1.5 rounded-full bg-current" />
                </SelectPrimitive.ItemIndicator>
                <SelectPrimitive.ItemText>{option.label}</SelectPrimitive.ItemText>
              </SelectPrimitive.Item>
            ))}
          </SelectPrimitive.Viewport>
        </SelectPrimitive.Content>
      </SelectPrimitive.Portal>
    </SelectPrimitive.Root>
  );
}
