import type { ReactNode } from "react";

export interface Column<T> {
  key: string;
  label: string;
  render: (row: T) => ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string | number;
  onRowClick?: (row: T) => void;
  empty?: string;
}

export function DataTable<T>({ columns, rows, rowKey, onRowClick, empty = "Nothing to show." }: DataTableProps<T>) {
  if (rows.length === 0) {
    return <div className="rounded-lg border border-zinc-200 p-8 text-center text-sm text-zinc-500 dark:border-zinc-800">{empty}</div>;
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-zinc-200 dark:border-zinc-800">
      <table className="min-w-full divide-y divide-zinc-200 text-left text-sm dark:divide-zinc-800">
        <thead className="bg-zinc-100/70 text-xs uppercase tracking-wide text-zinc-500 dark:bg-zinc-900/70">
          <tr>
            {columns.map((column) => (
              <th key={column.key} scope="col" className={`px-4 py-3 font-medium ${column.className ?? ""}`}>
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
          {rows.map((row) => (
            <tr
              key={rowKey(row)}
              onClick={() => onRowClick?.(row)}
              className={onRowClick ? "cursor-pointer hover:bg-zinc-100/60 dark:hover:bg-zinc-900/60" : ""}
            >
              {columns.map((column) => (
                <td key={column.key} className={`px-4 py-3 align-top ${column.className ?? ""}`}>
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
