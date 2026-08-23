import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

/** Upload a CSV and download the enriched sheet.
 *
 * This is the evaluation flow made visible: six columns of distributor
 * shorthand in, the full 252-column delivery format out. Uploading replaces the
 * current run, so the review queue and search reflect the new file immediately.
 */
export default function UploadBar({ onDark = false }: { onDark?: boolean }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();
  const [note, setNote] = useState<string | null>(null);

  const upload = useMutation({
    mutationFn: (file: File) => api.uploadCsv(file),
    onSuccess: (res) => {
      setNote(`Enriching ${res.rows.toLocaleString()} rows from ${res.input_file}…`);
      // Drop every cached view so they refetch against the new run.
      queryClient.clear();
    },
    onError: (e: Error) => setNote(e.message),
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          hidden
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) upload.mutate(file);
            // Reset so re-picking the same file fires change again.
            e.target.value = "";
          }}
        />
        <button
          className="btn btn--accent"
          onClick={() => inputRef.current?.click()}
          disabled={upload.isPending}
        >
          {upload.isPending ? "Uploading…" : "Upload a CSV"}
        </button>
        <a
          className={onDark ? "btn btn--ghost-light" : "btn"}
          href={api.exportUrl()}
          download
        >
          Download enriched sheet
        </a>
      </div>

      {note ? (
        <div
          className="tiny"
          style={{
            color: upload.isError
              ? "var(--critical)"
              : onDark
                ? "rgba(255,255,255,.72)"
                : "var(--ink-secondary)",
          }}
        >
          {note}
        </div>
      ) : (
        <div
          className="tiny"
          style={{ color: onDark ? "rgba(255,255,255,.55)" : "var(--ink-muted)" }}
        >
          Needs the six input columns: Mfg_Part_Num, Part_Desc, E1_Brand, Unilog_Brand, DIB_Brand,
          Part_Manuf
        </div>
      )}
    </div>
  );
}
