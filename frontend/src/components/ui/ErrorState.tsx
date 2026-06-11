"use client";

export function ErrorState({
  message,
  onRetry,
  compact = false,
}: {
  message: string;
  onRetry?: () => void;
  compact?: boolean;
}) {
  return (
    <div
      className={`flex flex-col items-center justify-center border border-risk/50 bg-risk/10 text-center ${
        compact ? "gap-2 p-5" : "gap-3 p-10"
      }`}
    >
      <div className="text-xs uppercase tracking-[0.2em] text-[#C98A8A]">
        Connection Interrupted
      </div>
      <p
        className={`font-serif text-text-primary ${compact ? "text-base" : "text-xl"}`}
      >
        {message}
      </p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-1 border border-gold/60 px-4 py-1.5 text-xs uppercase tracking-[0.2em] text-gold transition-colors hover:bg-gold hover:text-ink"
        >
          Retry
        </button>
      ) : null}
    </div>
  );
}
