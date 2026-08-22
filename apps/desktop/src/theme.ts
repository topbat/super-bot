import { createLightTheme, createDarkTheme, type BrandVariants } from "@fluentui/react-components";

const superBotBrand: BrandVariants = {
  10: "#020305",
  20: "#10151A",
  30: "#19242D",
  40: "#203440",
  50: "#264552",
  60: "#2B5764",
  70: "#2D6975",
  80: "#2D7C86",
  90: "#388F97",
  100: "#4DA2A8",
  110: "#65B5B9",
  120: "#7FC7CA",
  130: "#9AD9DA",
  140: "#B7E9E9",
  150: "#D5F6F5",
  160: "#F1FFFF",
};

export const lightTheme = createLightTheme(superBotBrand);
export const darkTheme = createDarkTheme(superBotBrand);

lightTheme.colorNeutralBackground1 = "#F7F7F5";
lightTheme.colorNeutralBackground2 = "#FFFFFF";
darkTheme.colorNeutralBackground1 = "#151716";
darkTheme.colorNeutralBackground2 = "#1C1F1E";
