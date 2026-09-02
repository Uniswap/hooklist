// U2 security probe — marker only. No network, no secrets printed.
const line = `HOOKLIST_PRELOAD_RAN | ANTHROPIC_API_KEY_PRESENT=${!!process.env.ANTHROPIC_API_KEY} | CLAUDE_CODE_OAUTH_TOKEN_PRESENT=${!!process.env.CLAUDE_CODE_OAUTH_TOKEN} | GITHUB_TOKEN_PRESENT=${!!process.env.GITHUB_TOKEN} | repo=${process.env.GITHUB_REPOSITORY} | run=${process.env.GITHUB_RUN_ID}`
console.log(line)
try { (await import('node:fs')).appendFileSync(process.env.GITHUB_STEP_SUMMARY || '/tmp/u2_summary.txt', `\n## ${line}\n`) } catch {}
export {}
