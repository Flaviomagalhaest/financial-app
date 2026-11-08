/** Ícones de linha da casca (ticket 204), desenhados aqui para não depender de biblioteca; a cor vem do texto. */
const TRACOS = {
  hoje: (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
    </>
  ),
  mes: (
    <>
      <rect x="3" y="5" width="18" height="16" rx="2.5" />
      <path d="M3 10h18M8 3v4M16 3v4" />
    </>
  ),
  cartoes: (
    <>
      <rect x="2.5" y="5" width="19" height="14" rx="2.5" />
      <path d="M2.5 10h19M6.5 15h4" />
    </>
  ),
  historico: (
    <>
      <path d="M3.5 12a8.5 8.5 0 1 0 2.6-6.1" />
      <path d="M3 4v4.5h4.5M12 7.5V12l3 2" />
    </>
  ),
  futuro: <path d="M3 17l6-6 4 4 8-8M15 7h6v6" />,
  lupa: (
    <>
      <circle cx="11" cy="11" r="6.5" />
      <path d="M16 16l4.5 4.5" />
    </>
  ),
  mais: <path d="M12 5v14M5 12h14" />,
  estrela: <path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z" />,
  pastas: <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />,
} as const;

export type NomeDoIcone = keyof typeof TRACOS;

export function Icone({ nome }: { nome: NomeDoIcone }) {
  return (
    <svg className="icone" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      {TRACOS[nome]}
    </svg>
  );
}
