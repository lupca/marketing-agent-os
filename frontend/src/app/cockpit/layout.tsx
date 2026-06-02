export default function CockpitRootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 selection:bg-violet-500/30">
      <main className="max-w-[1600px] mx-auto p-4 md:p-8 h-screen flex flex-col">
        {children}
      </main>
    </div>
  );
}
