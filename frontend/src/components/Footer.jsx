export default function Footer() {
  return (
    <footer className="border-t border-[#334155] mt-10">
      <div className="max-w-6xl mx-auto px-4 py-8 text-center space-y-3">
        <p className="text-sm text-slate-400 max-w-2xl mx-auto">
          🔒 <span className="text-slate-300 font-medium">BankLens</span> processes your files entirely in-memory.
          No data is stored on our servers. Your bank statements are never retained.
        </p>
        <p className="text-xs text-slate-600">
          Built with ❤️
        </p>
      </div>
    </footer>
  );
}
