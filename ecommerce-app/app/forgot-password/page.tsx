import ForgotPasswordForm from "@/components/ForgotPasswordForm";

export const metadata = {
  title: "Forgot password · Clickbound",
};

export default function ForgotPasswordPage() {
  return (
    <main className="flex min-h-[calc(100vh-104px)] items-center justify-center p-6">
      <ForgotPasswordForm />
    </main>
  );
}
