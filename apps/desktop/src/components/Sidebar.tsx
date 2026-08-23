import { Avatar } from "@fluentui/react-avatar";
import { Button } from "@fluentui/react-button";
import { Tooltip } from "@fluentui/react-tooltip";
import { CalendarDots } from "@phosphor-icons/react/dist/csr/CalendarDots";
import { Browser } from "@phosphor-icons/react/dist/csr/Browser";
import { ChatsCircle } from "@phosphor-icons/react/dist/csr/ChatsCircle";
import { Cpu } from "@phosphor-icons/react/dist/csr/Cpu";
import { Database } from "@phosphor-icons/react/dist/csr/Database";
import { GearSix } from "@phosphor-icons/react/dist/csr/GearSix";
import { ListChecks } from "@phosphor-icons/react/dist/csr/ListChecks";
import { Plus } from "@phosphor-icons/react/dist/csr/Plus";
import { PuzzlePiece } from "@phosphor-icons/react/dist/csr/PuzzlePiece";
import { Robot } from "@phosphor-icons/react/dist/csr/Robot";
import { ShieldCheck } from "@phosphor-icons/react/dist/csr/ShieldCheck";

import type { Bot } from "@superbot/contracts";

interface SidebarProps {
  bots: Bot[];
  activeSection?: string;
  onSectionChange?: (section: string) => void;
  selectedBotId?: string;
  onSelectBot?: (botId: string) => void;
  onCreateBot?: () => void;
}

const sections = [
  [ChatsCircle, "对话", "chat"],
  [Browser, "浏览器", "browser"],
  [CalendarDots, "例行任务", "routines"],
  [PuzzlePiece, "技能", "skills"],
  [ShieldCheck, "审批中心", "approvals"],
  [Cpu, "模型中心", "models"],
  [ListChecks, "审计记录", "audit"],
  [Database, "Worker", "workers"],
] as const;

export function Sidebar({ bots, activeSection = "chat", onSectionChange, selectedBotId, onSelectBot, onCreateBot }: SidebarProps) {
  return (
    <nav className="sidebar" aria-label="主导航">
      <div className="brand-row">
        <span className="brand-mark" aria-hidden="true"><Robot weight="fill" /></span>
        <span className="brand-name">SUPER BOT</span>
      </div>

      <div className="nav-section" aria-label="工作区">
        {sections.map(([Icon, label, id]) => (
          <Button
            key={label}
            appearance={activeSection === id ? "subtle" : "transparent"}
            icon={<Icon />}
            className={activeSection === id ? "nav-item nav-item-active" : "nav-item"}
            onClick={() => onSectionChange?.(id)}
          >
            {label}
          </Button>
        ))}
      </div>

      <div className="bot-heading">
        <span>BOT</span>
        <Tooltip content="创建 Bot" relationship="label">
          <Button appearance="subtle" size="small" icon={<Plus />} aria-label="创建 Bot" onClick={onCreateBot} />
        </Tooltip>
      </div>
      <div className="bot-list">
        {bots.map((bot) => (
          <button
            className={bot.id === selectedBotId ? "bot-item bot-item-active" : "bot-item"}
            key={bot.id}
            onClick={() => onSelectBot?.(bot.id)}
          >
            <Avatar name={bot.name} color="teal" size={28} />
            <span className="bot-copy">
              <span>{bot.name}</span>
              <span className="muted truncate">{bot.role}</span>
            </span>
            <span className="status-dot" title="在线" />
          </button>
        ))}
      </div>

      <Button appearance="transparent" icon={<GearSix />} className="nav-item sidebar-settings">
        设置
      </Button>
    </nav>
  );
}
