"use client";

import { useEffect, useState } from "react";

type HealthResponse = {
  api: string;
  database: string;
};

type BackendState = "checking" | "online" | "offline";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [backendState, setBackendState] = useState<BackendState>("checking");
  const [databaseState, setDatabaseState] = useState<"checking" | "connected" | "disconnected">(
    "checking"
  );

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((response) => {
        if (!response.ok) throw new Error("Backend respondeu com erro");
        return response.json() as Promise<HealthResponse>;
      })
      .then((data) => {
        setBackendState("online");
        setDatabaseState(data.database === "connected" ? "connected" : "disconnected");
      })
      .catch(() => {
        setBackendState("offline");
        setDatabaseState("disconnected");
      });
  }, []);

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-6 p-16 text-center">
      <h1 className="text-3xl font-semibold">ARGOS</h1>
      <p className="text-zinc-600">Sistema de monitoramento de ativos</p>

      <div className="flex flex-col gap-2 text-left">
        <p>
          Backend: <StatusLabel state={backendState} onLabel="Online" offLabel="Offline" />
        </p>
        <p>
          Database:{" "}
          <StatusLabel
            state={databaseState === "connected" ? "online" : databaseState === "checking" ? "checking" : "offline"}
            onLabel="Connected"
            offLabel="Disconnected"
          />
        </p>
      </div>
    </div>
  );
}

function StatusLabel({
  state,
  onLabel,
  offLabel,
}: {
  state: BackendState;
  onLabel: string;
  offLabel: string;
}) {
  if (state === "checking") return <span>Verificando...</span>;
  return <span>{state === "online" ? onLabel : offLabel}</span>;
}
