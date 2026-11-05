import { environment, showHUD } from "@raycast/api";
import { execFile } from "child_process";
import { existsSync } from "fs";
import { join } from "path";
import { promisify } from "util";

const runScript = promisify(execFile);

// Raycast subprocesses get a minimal PATH, so uv has to be located by absolute path.
const UV_CANDIDATES = [
  "/opt/homebrew/bin/uv",
  "/usr/local/bin/uv",
  `${process.env.HOME}/.local/bin/uv`,
];

type CommandProps = { arguments: { label?: string } };

export default async function Command(props: CommandProps) {
  const uv = UV_CANDIDATES.find(existsSync);
  if (!uv) {
    await showHUD("uv not found — install it with: brew install uv");
    return;
  }

  const script = join(environment.assetsPath, "hidemyemail.py");
  const label = props.arguments.label?.trim() ?? "";

  try {
    const { stdout } = await runScript(
      uv,
      ["run", "--quiet", "--script", script, label],
      { timeout: 120_000 },
    );
    await showHUD(stdout.trim());
  } catch (error) {
    const failure = error as {
      stderr?: string;
      stdout?: string;
      message: string;
    };
    const detail = (failure.stderr || failure.stdout || failure.message)
      .trim()
      .split("\n")
      .pop();
    await showHUD(`Hide My Email failed — ${detail}`);
  }
}
