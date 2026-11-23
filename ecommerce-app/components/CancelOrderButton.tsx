"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useToasts } from "@/lib/toast-context";

export default function CancelOrderButton({ orderId }: { orderId: string }) {
  const router = useRouter();
  const { success, error } = useToasts();
  const [cancelling, setCancelling] = useState(false);

  async function handleCancel() {
    if (!confirm("Cancel this order? Stock will be returned and the payment refunded.")) return;
    setCancelling(true);

    const res = await fetch(`/api/orders/${orderId}/cancel`, { method: "POST" });

    setCancelling(false);

    if (!res.ok) {
      const data = await res.json();
      error(typeof data.error === "string" ? data.error : "Couldn't cancel the order");
      return;
    }

    success("Order cancelled");
    router.refresh();
  }

  return (
    <button
      type="button"
      onClick={handleCancel}
      disabled={cancelling}
      className="rounded-lg px-3 py-1.5 text-sm text-danger border border-danger/30 hover:bg-danger/10 transition-colors disabled:opacity-50 press-down"
    >
      {cancelling ? "Cancelling..." : "Cancel order"}
    </button>
  );
}
