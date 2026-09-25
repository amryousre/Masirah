"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/button/button";
import { Dialog } from "@/components/dialog/dialog";
import { Tabs } from "@/components/tabs/tabs";
import { Toast, ToastRegion } from "@/components/toast/toast";

// The interactive specimens on the design page. Each keeps its own state; none of them saves.

export function TabsDemo() {
  const t = useTranslations("gallery.tabs");
  const [selected, setSelected] = useState("candidates");
  const items = [
    { id: "candidates", label: t("candidates"), count: 42 },
    { id: "review", label: t("reviewQueue"), count: 3 },
    { id: "board", label: t("board") },
    { id: "activity", label: t("activity") },
    { id: "scorecard", label: t("scorecard"), disabled: true },
    { id: "messages", label: t("messages"), loading: true },
    { id: "channels", label: t("channels"), error: t("channelsFailed") },
  ];
  const current = items.find((item) => item.id === selected) ?? items[0];
  return (
    <Tabs label={t("label")} items={items} selected={selected} onSelect={setSelected}>
      <p>{t("panel", { tab: current?.label ?? "" })}</p>
    </Tabs>
  );
}

export function DialogDemo() {
  const t = useTranslations("gallery.dialog");
  const [open, setOpen] = useState(false);
  const close = () => {
    setOpen(false);
  };
  return (
    <>
      <Button
        variant="secondary"
        onClick={() => {
          setOpen(true);
        }}
      >
        {t("open")}
      </Button>
      <Dialog
        open={open}
        title={t("heading")}
        onClose={close}
        actions={
          <>
            <Button variant="primary" onClick={close} autoFocus>
              {t("keep")}
            </Button>
            <Button variant="secondary" onClick={close}>
              {t("discard")}
            </Button>
          </>
        }
      >
        <p>{t("body")}</p>
      </Dialog>
    </>
  );
}

export function ToastsDemo() {
  const t = useTranslations("gallery.toasts");
  const [shown, setShown] = useState({ done: true, rejected: true, failed: true });
  const hide = (key: keyof typeof shown) => () => {
    setShown((current) => ({ ...current, [key]: false }));
  };
  return (
    <ToastRegion placement="inline">
      {shown.done && (
        <Toast
          tone="success"
          message={t("batchDone")}
          action={{ label: t("openRanking"), onAction: hide("done") }}
          onDismiss={hide("done")}
        />
      )}
      {shown.rejected && (
        <Toast
          tone="neutral"
          message={t("rejected")}
          action={{ label: t("undo"), onAction: hide("rejected") }}
          onDismiss={hide("rejected")}
        />
      )}
      {shown.failed && (
        <Toast
          tone="error"
          message={t("sendFailed")}
          action={{ label: t("retry"), onAction: hide("failed") }}
          onDismiss={hide("failed")}
        />
      )}
    </ToastRegion>
  );
}
