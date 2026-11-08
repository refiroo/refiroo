/**
 * A job group's name (0.13 JG): an assistant task is named after its workbook, so a file's
 * extension is set apart as a small tag ("Leads" [xlsx]) and the name reads as a name.
 */

const EXTENSION = /^(.+)\.(xlsx|xlsm|xls|csv)$/i;

export function OriginName({ name }: { name: string }) {
  const parts = EXTENSION.exec(name.trim());
  if (!parts) return <>{name}</>;
  return (
    <span className="origin-name">
      <span>{parts[1]}</span>
      <span className="file-ext">{parts[2].toLowerCase()}</span>
    </span>
  );
}
