import { Avatar } from "@fluentui/react-avatar";

import type { Bot } from "@superbot/contracts";

export function BotList({ bots, onSelect }: { bots: Bot[]; onSelect: (bot: Bot) => void }) {
  return <div className="entity-list">{bots.map((bot) => <button key={bot.id} onClick={() => onSelect(bot)}><Avatar name={bot.name} /><span><strong>{bot.name}</strong><small>{bot.role}</small></span></button>)}</div>;
}
