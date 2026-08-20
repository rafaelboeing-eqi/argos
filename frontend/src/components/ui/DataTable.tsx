import type { ReactNode } from "react";

export type DataTableColumn<T> = {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  align?: "left" | "right";
};

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  onRowClick,
}: {
  columns: DataTableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string | number;
  onRowClick?: (row: T) => void;
}) {
  return (
    <div className="overflow-x-auto rounded-xl border border-argos-100 bg-white">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-argos-100 text-xs uppercase tracking-wide text-argos-500">
            {columns.map((column) => (
              <th key={column.key} className={`px-4 py-2.5 font-medium ${column.align === "right" ? "text-right" : "text-left"}`}>
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={rowKey(row)}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={`border-b border-argos-50 last:border-0 ${onRowClick ? "cursor-pointer hover:bg-argos-50/60" : ""}`}
            >
              {columns.map((column) => (
                <td key={column.key} className={`px-4 py-2.5 ${column.align === "right" ? "text-right" : ""}`}>
                  {column.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
