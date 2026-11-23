export type ShippingMethodId = "STANDARD" | "EXPRESS";

export interface ShippingMethod {
  id: ShippingMethodId;
  label: string;
  eta: string;
  cost: number;
  freeThreshold: number | null;
}

export const SHIPPING_METHODS: ShippingMethod[] = [
  {
    id: "STANDARD",
    label: "Standard",
    eta: "5-7 business days",
    cost: 499,
    freeThreshold: 7500,
  },
  {
    id: "EXPRESS",
    label: "Express",
    eta: "2-3 business days",
    cost: 1299,
    freeThreshold: null,
  },
];

export function getShippingMethod(id: string): ShippingMethod | undefined {
  return SHIPPING_METHODS.find((m) => m.id === id);
}

export function calcShippingCost(method: ShippingMethod, subtotal: number): number {
  if (method.freeThreshold !== null && subtotal >= method.freeThreshold) {
    return 0;
  }
  return method.cost;
}
