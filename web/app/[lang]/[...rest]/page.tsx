import { notFound } from "next/navigation";

// Any path under a locale that matches no route gets the translated not-found page.
export default function Unknown() {
  notFound();
}
