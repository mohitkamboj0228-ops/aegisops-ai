import Sidebar from "./Sidebar";
import Header from "./Header";
interface Props {
  children: React.ReactNode;
}

export default function MainLayout({ children }: Props) {
  return (
    <div className="flex bg-slate-950 text-white min-h-screen">
      <Sidebar />

      <div className="flex-1">
        <Header />

        <main className="p-8">{children}</main>
      </div>
    </div>
  );
}