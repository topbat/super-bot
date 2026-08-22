import { Avatar, Button, Tooltip } from "@fluentui/react-components";
import {
  CalendarDots,
  ChatsCircle,
  GearSix,
  Plus,
  PuzzlePiece,
  Robot,
  ShieldCheck,
} from "@phosphor-icons/react";

import type { Bot } from "@superbot/contracts";

interface SidebarProps {
  bots: Bot[];
}

const sections = [
  [ChatsCircle, "对话"],
  [CalendarDots, "例行任务"],
  [PuzzlePiece, "技能"],
  [ShieldCheck, "审批中心"],
] as const;

export function Sidebar({ bots }: SidebarProps) {
  return (
    <nav className="sidebar" aria-label="主导航">
      <div className="brand-row">
        <span className="brand-mark" aria-hidden="true"><Robot weight="fill" /></span>
        <span className="brand-name">SUPER BOT</span>
      </div>

      <div className="nav-section" aria-label="工作区">
        {sections.map(([Icon, label], index) => (
          <Button
            key={label}
            appearance={index === 0 ? "subtle" : "transparent"}
            icon={<Icon />}
            className={index === 0 ? "nav-item nav-item-active" : "nav-item"}
          >
            {label}
          </Button>
        ))}
      </div>

      <div className="bot-heading">
        <span>BOT</span>
        <Tooltip content="创建 Bot" relationship="label">
          <Button appearance="subtle" size="small" icon={<Plus />} aria-label="创建 Bot" />
        </Tooltip>
      </div>
      <div className="bot-list">
        {bots.map((bot, index) => (
          <button className={index === 0 ? "bot-item bot-item-active" : "bot-item"} key={bot.id}>
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
