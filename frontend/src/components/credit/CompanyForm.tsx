"use client";

import { type FormEvent, useState } from "react";

import { postJson } from "@/lib/api";
import type { Company } from "@/types/credit";

export function CompanyForm({ onCreated }: { onCreated: (company: Company) => void }) {
  const [nome, setNome] = useState("");
  const [setor, setSetor] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!nome.trim() || !setor.trim()) return;

    setSubmitting(true);
    setError(null);
    try {
      const company = await postJson<Company>("/api/companies", { nome, setor });
      onCreated(company);
      setNome("");
      setSetor("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form
      onSubmit={submit}
      className="flex flex-wrap items-end gap-3 rounded-2xl bg-white p-4 shadow-sm ring-1 ring-argos-100"
    >
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium uppercase tracking-wide text-argos-500" htmlFor="nome">
          Nome
        </label>
        <input
          id="nome"
          value={nome}
          onChange={(event) => setNome(event.target.value)}
          className="rounded-lg border border-argos-200 px-3 py-2 text-sm"
          placeholder="Empresa S.A."
        />
      </div>
      <div className="flex flex-col gap-1">
        <label className="text-xs font-medium uppercase tracking-wide text-argos-500" htmlFor="setor">
          Setor
        </label>
        <input
          id="setor"
          value={setor}
          onChange={(event) => setSetor(event.target.value)}
          className="rounded-lg border border-argos-200 px-3 py-2 text-sm"
          placeholder="Agro"
        />
      </div>
      <button
        type="submit"
        disabled={submitting}
        className="rounded-full bg-argos-400 px-4 py-2 text-sm font-medium text-white transition hover:bg-argos-500 disabled:opacity-50"
      >
        {submitting ? "Criando..." : "Nova empresa"}
      </button>
      {error && <p className="w-full text-sm text-red-600">{error}</p>}
    </form>
  );
}
