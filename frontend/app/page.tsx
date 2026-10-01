import Header from "@/components/layout/Header";
import Sidebar from "@/components/layout/Sidebar";
import Footer from "@/components/layout/Footer";

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 p-6 space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-8">
            <h1 className="text-3xl font-bold tracking-tight text-white mb-2">
              Project Stardust Dashboard
            </h1>
            <p className="text-slate-400 max-w-2xl">
              Cross-sensor satellite fire normalization platform bridging MODIS & VIIRS
              to power high-accuracy agricultural burning calendars.
            </p>
          </div>
        </main>
      </div>
      <Footer />
    </div>
  );
}
