"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

type FormErrors = Record<string, string>;

interface Category {
  id: string;
  name: string;
}

export default function EditProductPage() {
  const params = useParams<{ id: string }>();
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
  const [deleting, setDeleting] = useState(false);
  const [notFound, setNotFound] = useState(false);

  function toLocalInput(iso: string) {
    const d = new Date(iso);
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(
      d.getHours(),
    )}:${pad(d.getMinutes())}`;
  }

  useEffect(() => {
    Promise.all([
      fetch(`/api/products/${params.id}`).then((res) => {
        if (!res.ok) {
          setNotFound(true);
          return null;
        }
        return res.json();
      }),
      fetch("/api/categories").then((res) => res.json()),
    ]).then(([productData, categoryData]) => {
      setCategories(categoryData.categories ?? []);
      if (!productData) return;
      const p = productData.product;
      setForm({
        name: p.name,
        description: p.description,
        price: (p.price / 100).toFixed(2),
        salePrice: p.salePrice != null ? (p.salePrice / 100).toFixed(2) : "",
        saleEndsAt: p.saleEndsAt ? toLocalInput(p.saleEndsAt) : "",
        imageUrl: p.imageUrl ?? "",
        categoryId: p.categoryId ?? "",
        stock: String(p.stock),
      });
    });
  }, [params.id]);

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

    const res = await fetch(`/api/products/${params.id}`, {
      method: "PATCH",
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

  async function handleDelete() {
    if (!confirm("Are you sure you want to delete this product?")) return;
    setErrors({});
    setDeleting(true);

    const res = await fetch(`/api/products/${params.id}`, { method: "DELETE" });

    setDeleting(false);

    if (!res.ok) {
      const data = await res.json();
      setErrors(extractErrors(data.error));
      return;
    }

    router.push("/admin/products");
    router.refresh();
  }

  if (notFound) {
    return (
      <main className="max-w-sm mx-auto p-6 mt-12">
        <p className="text-text-muted">Product not found.</p>
      </main>
    );
  }

  return (
    <main className="max-w-sm mx-auto p-6 mt-12">
      <h1 className="font-display text-2xl font-bold mb-6">EDIT PRODUCT</h1>

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
          Leave sale price blank to end the flash deal. Ends is optional.
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
          {loading ? "Saving..." : "Save changes"}
        </button>
      </form>

      <button
        type="button"
        onClick={handleDelete}
        disabled={deleting}
        className="w-full rounded-lg px-3 py-2 mt-3 text-sm text-danger border border-danger/30 hover:bg-danger/10 transition-colors disabled:opacity-50"
      >
        {deleting ? "Deleting..." : "Delete product"}
      </button>
    </main>
  );
}
