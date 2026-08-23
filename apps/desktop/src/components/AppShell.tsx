import type { ReactNode } from "react";

interface AppShellProps {
  sidebar: ReactNode;
  children: ReactNode;
  inspector?: ReactNode;
}

export function AppShell({ sidebar, children, inspector }: AppShellProps) {
  return (
    <div className={inspector ? "app-shell" : "app-shell inspector-collapsed"}>
      {sidebar}
      {children}
      {inspector}
    </div>
  );
}
