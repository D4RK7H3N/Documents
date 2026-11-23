export interface Priceable {
  price: number;
  salePrice: number | null;
  saleEndsAt: Date | string | null;
}

export function isOnSale(p: Priceable, now = new Date()): boolean {
  if (p.salePrice == null || p.salePrice <= 0) return false;
  if (p.saleEndsAt == null) return true;
  return new Date(p.saleEndsAt).getTime() > now.getTime();
}

export function effectivePrice(p: Priceable): number {
  return isOnSale(p) ? (p.salePrice as number) : p.price;
}

export function salePercent(p: Priceable): number | null {
  if (!isOnSale(p) || p.price <= 0) return null;
  return Math.round((1 - (p.salePrice as number) / p.price) * 100);
}
