import type { FieldControlProps } from "@/ui/FormField";

/**
 * A file chooser (U-D14): the one file input of the model draft dialog and the import dialog. It
 * hands the chosen file, or none when the choice is cleared, to `onFile`; a `FormField` around it
 * passes its label, help and error through `control`.
 */
export function FileField({
  accept,
  onFile,
  control,
  disabled = false,
}: {
  accept: string;
  onFile: (file: File | undefined) => void;
  control?: FieldControlProps;
  disabled?: boolean;
}) {
  return (
    <input
      {...control}
      className="file-field"
      type="file"
      accept={accept}
      disabled={disabled}
      onChange={(event) => onFile(event.target.files?.[0])}
    />
  );
}
