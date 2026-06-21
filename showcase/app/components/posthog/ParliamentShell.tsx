"use client";

type Tab = "hearing" | "compare" | "training";

const NAV: { id: Tab; label: string; icon: string; color: string }[] = [
  { id: "hearing", label: "Chamber", icon: "◉", color: "var(--primary-3000)" },
  { id: "compare", label: "Benchmarks", icon: "▥", color: "var(--brand-blue)" },
  { id: "training", label: "Weights", icon: "◈", color: "var(--brand-yellow)" },
];

function MenuClock() {
  const now = new Date();
  const time = now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return (
    <span className="mono ac-menu-clock" suppressHydrationWarning>
      {time}
    </span>
  );
}

export function ParliamentShell({
  tab,
  onTabChange,
  windowTitle,
  windowSubtitle,
  windowBadge,
  toolbar,
  children,
}: {
  tab: Tab;
  onTabChange: (t: Tab) => void;
  windowTitle: string;
  windowSubtitle?: string;
  windowBadge?: React.ReactNode;
  toolbar?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="ac-desktop">
      <header className="ac-menubar">
        <div className="ac-menubar-left">
          <span className="ac-menubar-mark">AC</span>
          <span className="ac-menubar-app">Attention Commons</span>
          <nav className="ac-menubar-nav" aria-hidden>
            <span>Hearing</span>
            <span>Record</span>
            <span>Window</span>
          </nav>
        </div>
        <div className="ac-menubar-right">
          <span className="ac-menubar-pill">
            <span className="ac-menubar-dot" /> MCP online
          </span>
          <MenuClock />
        </div>
      </header>

      <div className="ac-body">
        <aside className="ac-rail">
          <div className="ac-rail-brand">
            <span className="ac-rail-logo">🦔</span>
            <div>
              <div className="ac-rail-name">Parliament</div>
              <div className="ac-rail-env mono">context-window · HUD</div>
            </div>
          </div>

          <div className="ph-nav-section">Views</div>
          {NAV.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onTabChange(item.id)}
              className={`ac-rail-item${tab === item.id ? " ac-rail-item-active" : ""}`}
            >
              <span className="ac-rail-icon" style={{ color: item.color }}>
                {item.icon}
              </span>
              {item.label}
            </button>
          ))}

          <div className="ac-rail-footer">
            <div className="ac-rail-stat">
              <span className="mono">500</span>
              <span>worlds</span>
            </div>
            <div className="ac-rail-stat">
              <span className="mono">3</span>
              <span>policies</span>
            </div>
          </div>
        </aside>

        <main className="ac-stage">
          <div className="ac-window">
            <div className="ac-window-chrome">
              <div className="ac-traffic">
                <span className="ac-light ac-light-red" />
                <span className="ac-light ac-light-yellow" />
                <span className="ac-light ac-light-green" />
              </div>
              <div className="ac-window-titleblock">
                <h1 className="ac-window-title">{windowTitle}</h1>
                {windowSubtitle && <p className="ac-window-sub">{windowSubtitle}</p>}
              </div>
              {windowBadge}
            </div>

            {toolbar && <div className="ac-window-toolbar">{toolbar}</div>}

            <div className="ac-window-body">{children}</div>
          </div>
        </main>
      </div>
    </div>
  );
}
