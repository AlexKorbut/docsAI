export function ConfidenceBadge({ value }: { value: number }) {
  const level = value >= 80 ? 'high' : value >= 60 ? 'medium' : 'low';
  return (
    <span className={`confidence confidence-${level}`} title="Confidence score">
      {value}%
    </span>
  );
}
