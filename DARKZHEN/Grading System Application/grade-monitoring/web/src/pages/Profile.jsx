import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { profileApi } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Btn, Card, ErrorBanner, Field, PageHeader, SectionCard, Spinner, inputClass, useToast } from "../components/ui";

const ACCEPTED_TYPES = ["image/png", "image/jpeg", "image/webp"];

export default function Profile() {
  const { user, loading, refreshUser } = useAuth();
  const toast = useToast();
  const fileInput = useRef(null);
  const [form, setForm] = useState({ first_name: "", last_name: "", email: "", phone: "" });
  const [photoFile, setPhotoFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    if (user) {
      setForm({
        first_name: user.first_name || "",
        last_name: user.last_name || "",
        email: user.email || "",
        phone: user.phone || "",
      });
    }
  }, [user]);

  useEffect(() => {
    if (!photoFile) {
      setPreview(null);
      return;
    }
    const url = URL.createObjectURL(photoFile);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [photoFile]);

  if (loading || !user) return <Spinner />;

  const initials = (user.display_name || user.username || "?")
    .split(/[\s,]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
  const shownAvatar = preview || user.avatar_url;

  function pickPhoto(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    setError(null);
    if (!file) return;
    if (!ACCEPTED_TYPES.includes(file.type)) {
      setError({ message: "Photo must be a PNG, JPG or WEBP file." });
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      setError({ message: "Photo must be smaller than 2 MB." });
      return;
    }
    setPhotoFile(file);
  }

  async function uploadPhoto() {
    if (!photoFile) return;
    setUploading(true);
    setError(null);
    try {
      await profileApi.uploadAvatar(photoFile);
      setPhotoFile(null);
      await refreshUser();
      toast.success("Profile photo updated.");
    } catch (e) {
      setError(e);
    } finally {
      setUploading(false);
    }
  }

  async function removePhoto() {
    setUploading(true);
    setError(null);
    try {
      await profileApi.removeAvatar();
      setPhotoFile(null);
      await refreshUser();
      toast.success("Profile photo removed.");
    } catch (e) {
      setError(e);
    } finally {
      setUploading(false);
    }
  }

  async function saveDetails(event) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await profileApi.update(form);
      await refreshUser();
      toast.success("Profile details saved.");
    } catch (e) {
      setError(e);
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Account"
        title="My Profile"
        sub="Your personal details and profile photo. Usernames and roles are managed by the administrator."
      />
      {error && <div className="mb-space-sm"><ErrorBanner error={error} /></div>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-space-lg items-start">
        <Card className="p-space-lg flex flex-col items-center text-center gap-space-md">
          {shownAvatar ? (
            <img src={shownAvatar} alt="Profile photo" className="w-24 h-24 rounded-full object-cover border border-outline-variant" />
          ) : (
            <div className="w-24 h-24 rounded-full bg-primary-container text-on-primary flex items-center justify-center text-2xl font-bold">
              {initials}
            </div>
          )}
          <div>
            <p className="font-headline-sm text-headline-sm text-on-surface">{user.display_name}</p>
            <p className="font-body-sm text-body-sm text-on-surface-variant">
              {user.username} · <span className="capitalize">{user.role}</span>
            </p>
          </div>
          <input ref={fileInput} type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={pickPhoto} aria-label="Choose profile photo" />
          <div className="flex flex-col w-full gap-space-sm">
            <Btn variant="secondary" icon="photo_camera" onClick={() => fileInput.current?.click()} disabled={uploading}>
              {photoFile ? "Choose a different photo" : "Choose photo"}
            </Btn>
            {photoFile && (
              <Btn icon="upload" onClick={uploadPhoto} disabled={uploading}>
                {uploading ? "Uploading…" : "Upload photo"}
              </Btn>
            )}
            {user.avatar_url && !photoFile && (
              <Btn variant="secondary" icon="delete" onClick={removePhoto} disabled={uploading}>
                Remove photo
              </Btn>
            )}
          </div>
          <p className="font-body-sm text-body-sm text-on-surface-variant">PNG, JPG or WEBP, up to 2 MB.</p>
        </Card>

        <SectionCard title="Personal details" sub="Shown in the portal header and on reports." className="lg:col-span-2">
          <form onSubmit={saveDetails} className="grid grid-cols-1 sm:grid-cols-2 gap-space-md">
            <Field label="First name">
              <input className={inputClass} value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} maxLength={150} required />
            </Field>
            <Field label="Last name">
              <input className={inputClass} value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} maxLength={150} required />
            </Field>
            <Field label="Email address" hint="Optional — used for account correspondence.">
              <input className={inputClass} type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
            </Field>
            <Field label="Phone number" hint="Optional.">
              <input className={inputClass} type="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} maxLength={32} />
            </Field>
            <div className="sm:col-span-2">
              <Btn type="submit" icon="save" disabled={saving}>
                {saving ? "Saving…" : "Save details"}
              </Btn>
            </div>
          </form>
        </SectionCard>
      </div>

      <SectionCard title="Security" sub="Keep your account protected with a fresh password.">
        <Link to="/change-password" className="inline-flex min-h-11 items-center gap-space-xs rounded-lg border border-outline-variant px-space-md font-label-md text-label-md text-primary hover:bg-surface-container-low">
          <span className="material-symbols-outlined text-base">lock</span>
          Change password
        </Link>
      </SectionCard>
    </>
  );
}
