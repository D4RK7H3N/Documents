"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type FormErrors = Record<string, string>;

interface Category {
  id: string;
  name: string;
}

export default function NewProductPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    name: "",
    description: "",
    price: "",
    salePrice: "",
    saleEndsAt: "",
    imageUrl: "",
    categoryId: "",
    stock: "0",
  });
  const [categories, setCategories] = useState<Category[]>([]);
  const [errors, setErrors] = useState<FormErrors>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch("/api/categories")
      .then((res) => res.json())
      .then((data) => setCategories(data.categories ?? []));
  }, []);

  function setField(key: keyof typeof form, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function extractErrors(error: unknown): FormErrors {
    if (typeof error === "string") return { form: error };
    if (error && typeof error === "object" && "fieldErrors" in error) {
      const e = error as { fieldErrors?: Record<string, string[]>; formErrors?: string[] };
      const out: FormErrors = {};
      for (const [key, messages] of Object.entries(e.fieldErrors ?? {})) {
        if (messages.length > 0) out[key] = messages[0];
      }
      if (e.formErrors?.length) out.form = e.formErrors[0];
      return out;
    }
    return { form: "Something went wrong" };
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErrors({});
    setLoading(true);

    const res = await fetch("/api/products", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: form.name,
        description: form.description,
        price: Math.round(parseFloat(form.price) * 100),
        salePrice: form.salePrice ? Math.round(parseFloat(form.salePrice) * 100) : null,
        saleEndsAt: form.saleEndsAt ? new Date(form.saleEndsAt).toISOString() : null,
        imageUrl: form.imageUrl || undefined,
        categoryId: form.categoryId || null,
        stock: parseInt(form.stock, 10),
      }),
    });

    setLoading(false);

    if (!res.ok) {
      const data = await res.json();
      setErrors(extractErrors(data.error));
      return;
    }

    router.push("/admin/products");
    router.refresh();
  }

  return (
    <main className="max-w-sm mx-auto p-6 mt-12">
      <h1 className="font-display text-2xl font-bold mb-6">NEW PRODUCT</h1>

      <form onSubmit={handleSubmit} className="glass-panel rounded-xl p-6 flex flex-col gap-4">
        <input
          type="text"
          placeholder="Name"
          className="input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
          value={form.name}
          onChange={(e) => setField("name", e.target.value)}
          required
        />
        {errors.name && <p className="text-xs text-danger -mt-2">{errors.name}</p>}

        <textarea
          placeholder="Description"
          className="input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
          rows={3}
          value={form.description}
          onChange={(e) => setField("description", e.target.value)}
          required
        />
        {errors.description && <p className="text-xs text-danger -mt-2">{errors.description}</p>}

        <input
          type="number"
          placeholder="Price (dollars)"
          min="0.01"
          step="0.01"
          className="input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
          value={form.price}
          onChange={(e) => setField("price", e.target.value)}
          required
        />
        {errors.price && <p className="text-xs text-danger -mt-2">{errors.price}</p>}

        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1">
            <input
              type="number"
              placeholder="Sale price $ (optional)"
              min="0.01"
              step="0.01"
              className="input-field rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
              value={form.salePrice}
              onChange={(e) => setField("salePrice", e.target.value)}
            />
            {errors.salePrice && (
              <p className="text-xs text-danger">{errors.salePrice}</p>
            )}
          </div>
          <div className="flex flex-col gap-1">
            <input
              type="datetime-local"
              placeholder="Sale ends"
              className="input-field rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
              value={form.saleEndsAt}
              onChange={(e) => setField("saleEndsAt", e.target.value)}
            />
            {errors.saleEndsAt && (
              <p className="text-xs text-danger">{errors.saleEndsAt}</p>
            )}
          </div>
        </div>
        <p className="text-xs text-text-muted -mt-2">
          Leave sale price blank for no flash deal. Ends is optional — blank means it stays active.
        </p>

        <input
          type="url"
          placeholder="Image URL (optional)"
          className="input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
          value={form.imageUrl}
          onChange={(e) => setField("imageUrl", e.target.value)}
        />
        {errors.imageUrl && <p className="text-xs text-danger -mt-2">{errors.imageUrl}</p>}

        <select
          className="input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
          value={form.categoryId}
          onChange={(e) => setField("categoryId", e.target.value)}
        >
          <option value="">No category</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        {errors.categoryId && <p className="text-xs text-danger -mt-2">{errors.categoryId}</p>}

        <input
          type="number"
          placeholder="Stock"
          min="0"
          step="1"
          className="input-field rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-accent-cyan/60"
          value={form.stock}
          onChange={(e) => setField("stock", e.target.value)}
          required
        />
        {errors.stock && <p className="text-xs text-danger -mt-2">{errors.stock}</p>}

        {errors.form && <p className="text-sm text-danger">{errors.form}</p>}

        <button
          type="submit"
          disabled={loading}
          className="btn-primary rounded-lg px-4 py-2 text-sm disabled:opacity-50"
        >
          {loading ? "Creating..." : "Create product"}
        </button>
      </form>
    </main>
  );
}
