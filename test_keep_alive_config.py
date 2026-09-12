from pathlib import Path


workflow = Path(".github/workflows/keep_alive.yml").read_text()

assert "cron: '23 * * * *'" in workflow
assert "permissions:\n  contents: write" in workflow
assert "git commit --allow-empty" in workflow
assert "if: always() && github.event.schedule == '41 3 1 * *'" in workflow
