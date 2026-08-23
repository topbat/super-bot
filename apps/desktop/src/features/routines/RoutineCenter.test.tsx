import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import { RoutineCenter } from "./RoutineCenter";

it("creates a timezone-aware routine for the active bot", async () => {
  const user = userEvent.setup();
  const onCreate = vi.fn().mockResolvedValue(undefined);
  render(<RoutineCenter routines={[]} botId="bot-1" onCreate={onCreate} />);

  await user.click(screen.getByRole("button", { name: "创建例程" }));
  await user.type(screen.getByLabelText("例程名称"), "每日简报");
  await user.type(screen.getByLabelText("Cron"), "0 9 * * 1-5");
  await user.type(screen.getByLabelText("任务说明"), "生成当天的一手资料简报");
  await user.click(screen.getByRole("button", { name: "保存例程" }));

  expect(onCreate).toHaveBeenCalledWith(expect.objectContaining({
    bot_id: "bot-1",
    timezone: "Asia/Shanghai",
    cron: "0 9 * * 1-5",
  }));
});
