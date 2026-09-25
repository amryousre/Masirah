import { useTranslations } from "next-intl";

import { Link } from "@/i18n/navigation";

import styles from "./not-found.module.css";

export default function NotFound() {
  const t = useTranslations("notFound");
  return (
    <main className={styles.page}>
      <h1 className={styles.title}>{t("title")}</h1>
      <p className={styles.body}>{t("body")}</p>
      <Link href="/" className={styles.link}>
        {t("back")}
      </Link>
    </main>
  );
}
