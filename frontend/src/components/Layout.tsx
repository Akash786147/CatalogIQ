import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, USE_MOCK } from "@/lib/api";

const NAV = [
  { to: "/", label: "Overview", end: true, icon: "◧" },
  { to: "/review", label: "Review queue", icon: "◉", badgeKey: "review" as const },
  { to: "/search", label: "Search proof", icon: "◈" },
];

const TITLES: Record<string, string> = {
  "/": "Run overview",
  "/review": "Review queue",
  "/search": "Search proof",
};

function useTheme() {
  const [theme, setTheme] = useState<"light" | "dark">(
    () => (localStorage.getItem("catalogiq-theme") as "light" | "dark") ?? "light",
  );
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("catalogiq-theme", theme);
    } catch {
      /* private mode — the theme just won't persist */
    }
  }, [theme]);
  return { theme, setTheme };
}

export default function Layout() {
  const { theme, setTheme } = useTheme();
  const { pathname } = useLocation();
  const { data: stats } = useQuery({ queryKey: ["run"], queryFn: api.getRunStats });

  const title = TITLES[pathname] ?? (pathname.startsWith("/review/") ? "Product detail" : "CatalogIQ");

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand__mark">C</div>
          <div>
            <div className="brand__name">CatalogIQ</div>
            <div className="brand__sub">Content Enrichment</div>
          </div>
        </div>

        <nav className="nav">
          <div className="nav__label">Workspace</div>
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `nav__item${isActive ? " nav__item--active" : ""}`}
            >
              <span className="nav__icon" aria-hidden>
                {item.icon}
              </span>
              {item.label}
              {item.badgeKey === "review" && stats ? (
                <span className="nav__badge">{stats.rows_needing_review}</span>
              ) : null}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar__foot">
          <span
            className="sidebar__status"
            title={
              USE_MOCK
                ? "Set VITE_USE_MOCK=false to hit the FastAPI backend"
                : "Connected to the FastAPI backend"
            }
          >
            <span className="sidebar__dot" />
            {USE_MOCK ? "Demo data — backend not connected" : "Live backend"}
          </span>
          <span>Built for Unilog · UniHack</span>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <div className="topbar__title">{title}</div>
          <div className="topbar__spacer" />
          {stats ? (
            <span className="tiny muted">
              {stats.input_file} · {stats.rows_total.toLocaleString()} rows
            </span>
          ) : null}
          <button
            className="btn btn--ghost"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            aria-label="Toggle colour theme"
            title="Toggle colour theme"
          >
            {theme === "dark" ? "☾" : "☀"}
          </button>
        </header>

        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
