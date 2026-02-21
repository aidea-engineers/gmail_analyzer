"use client";

import { useEffect, useState } from "react";
import { getProgressURL } from "@/lib/api";
import type { JobProgress } from "@/types";

interface Props {
  jobId: string;
  onComplete: (result: JobProgress) => void;
}

export default function ProgressBar({ jobId, onComplete }: Props) {
  const [progress, setProgress] = useState<JobProgress>({
    phase: "starting",
    current: 0,
    total: 0,
    message: "開始中...",
  });

  useEffect(() => {
    const url = getProgressURL(jobId);
    const eventSource = new EventSource(url);

    eventSource.onmessage = (event) => {
      const data: JobProgress = JSON.parse(event.data);
      setProgress(data);
      if (data.done) {
        eventSource.close();
        onComplete(data);
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
    };

    return () => eventSource.close();
  }, [jobId, onComplete]);

  const pct =
    progress.total > 0
      ? Math.round((progress.current / progress.total) * 100)
      : 0;

  return (
    <div className="mt-4 p-4 rounded-lg border" style={{ borderColor: "var(--border)" }}>
      <p className="text-sm mb-2">{progress.message}</p>
      <div className="w-full bg-slate-200 rounded-full h-3">
        <div
          className="h-3 rounded-full transition-all duration-300"
          style={{
            width: `${pct}%`,
            background: progress.phase === "error" ? "#ef4444" : "var(--primary)",
          }}
        />
      </div>
      {progress.total > 0 && (
        <p className="text-xs text-slate-500 mt-1">
          {progress.current} / {progress.total} ({pct}%)
        </p>
      )}
    </div>
  );
}
