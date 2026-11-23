export function flyToCart(rect: DOMRect, image?: string | null) {
  if (
    typeof window === "undefined" ||
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  ) {
    return;
  }
  window.dispatchEvent(
    new CustomEvent("fly-to-cart", {
      detail: {
        x: rect.left + rect.width / 2,
        y: rect.top + rect.height / 2,
        size: Math.max(rect.width, rect.height),
        image: image ?? null,
      },
    }),
  );
}
