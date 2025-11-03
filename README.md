# pf-verify (Public Skeleton)

Minimal CLI placeholder to demonstrate how OEP-288 verification *would* be wired.
This repo ships **no real cryptography** and uses **placeholders only**.
Do **NOT** use in production.

```bash
# local install
pip install -e .

# run (prints a markdown report)
pf-verify --receipt path/to/receipt.json --policy path/to/policy.yml --format markdown
