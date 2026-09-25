import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { hasLocale } from "next-intl";
import { getTranslations } from "next-intl/server";

import { AppFrame } from "@/components/app-frame/app-frame";
import { routing } from "@/i18n/routing";

import { CandidatesDemo, FrameUsage } from "../screening-demos";
import styles from "./frame.module.css";

export async function generateMetadata({
  params,
}: PageProps<"/[lang]/design/frame">): Promise<Metadata> {
  const { lang } = await params;
  if (!hasLocale(routing.locales, lang)) notFound();
  const t = await getTranslations({ locale: lang, namespace: "gallery" });
  return { title: t("frameLink") };
}

// The app frame around a real component, so it can be judged at full size in both directions.
export default async function FramePreview({ params }: PageProps<"/[lang]/design/frame">) {
  const { lang } = await params;
  if (!hasLocale(routing.locales, lang)) notFound();
  const t = await getTranslations("gallery.frame");
  return (
    <AppFrame
      organisation={t("organisation")}
      user={{ name: t("user"), email: t("email") }}
      reviewCount={5}
      usage={<FrameUsage />}
    >
      <div className={styles.page}>
        <h1 className={styles.title}>{t("heading")}</h1>
        <CandidatesDemo />
      </div>
    </AppFrame>
  );
}
