"use client";
import { useState } from "react";
import { signIn, signUp } from "@/app/actions";
import { ActionForm, Field } from "./ActionForm";

export function AuthForm() {
  const [mode, setMode] = useState<"in" | "up">("in");
  return (
    <div className="px-4">
      <div role="tablist" className="flex gap-1 rounded-full bg-wash p-1">
        {(["in", "up"] as const).map((m) => (
          <button
            key={m} role="tab" aria-selected={mode === m} type="button" onClick={() => setMode(m)}
            className={`min-h-11 flex-1 rounded-full font-semibold ${mode === m ? "bg-paper shadow-sm" : "text-ink-2"}`}
          >
            {m === "in" ? "Sign in" : "Create account"}
          </button>
        ))}
      </div>
      {mode === "in" ? (
        <ActionForm key="in" action={signIn} submit="Sign in">
          <Field label="Email" name="email" type="email" required autoComplete="email" />
          <Field label="Password" name="password" type="password" required autoComplete="current-password" />
        </ActionForm>
      ) : (
        <ActionForm key="up" action={signUp} submit="Create account">
          <Field label="Your name" name="display_name" required maxLength={60} autoComplete="name" />
          <Field label="Username" name="username" required maxLength={20} placeholder="priya_iyer" autoComplete="username"
            hint="Lowercase letters, numbers and underscore. People find you by this exact name." />
          <Field label="Email" name="email" type="email" required autoComplete="email" />
          <Field label="Password" name="password" type="password" required autoComplete="new-password" hint="At least 8 characters." />
        </ActionForm>
      )}
    </div>
  );
}
