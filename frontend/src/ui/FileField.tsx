import { useState } from "react";
import type { FieldControlProps } from "@/ui/FormField";

/**
 * A file chooser (U-D14): the one file input of the model draft dialog and the import dialog. It
 * hands the chosen file, or none when the choice is cleared, to `onFile`; a `FormField` around it
 * passes its label, help and error through `control`. The field is also a place to drop the file (0.17 UX1): a
 * file input takes a dropped file by itself, so the field is drawn as a drop area and lights up while a file
 * is held over it.
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
  const [over, setOver] = useState(false);
  return (
    <input
      {...control}
      className={`file-field${over ? " file-field-over" : ""}`}
      title="Choose a file, or drop one here"
      onDragEnter={() => setOver(true)}
      onDragLeave={() => setOver(false)}
      onDrop={() => setOver(false)}
      type="file"
      accept={accept}
      disabled={disabled}
      onChange={(event) => onFile(event.target.files?.[0])}
    />
  );
}
