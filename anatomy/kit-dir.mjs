// Finds the Anatomy kit (the folder holding kit/iso-kit.mjs). Set ANATOMY_DIR to it.
// The old local path is used only when ANATOMY_DIR is unset and that path exists.
import { existsSync } from "node:fs";

const LOCAL = "/Volumes/clear/Downloads/ada/anatomy/anatomy-skill";
const dir = process.env.ANATOMY_DIR || (existsSync(`${LOCAL}/kit/iso-kit.mjs`) ? LOCAL : "");
if (!dir || !existsSync(`${dir}/kit/iso-kit.mjs`)) {
  throw new Error("Anatomy kit not found. Set ANATOMY_DIR to the anatomy-skill folder (the one containing kit/iso-kit.mjs).");
}
export const KIT = dir;
