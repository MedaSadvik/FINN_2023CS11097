import Link from "next/link";

/** A person's name that opens their profile. `about` is a tracked company's ticker, so the draft email can mention it. */
export function PersonLink({ id, name, about, className = "font-semibold" }: { id: number; name: string; about?: string | null; className?: string }) {
  const href = `/network/${id}${about ? `?about=${encodeURIComponent(about)}` : ""}`;
  return <Link href={href} className={`${className} underline-offset-2 hover:underline`}>{name}</Link>;
}
