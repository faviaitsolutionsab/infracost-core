# Infracost Core GitHub Action

Generate a Terraform cost delta (current vs future) using the Infracost CLI and post/update a PR comment with a deterministic Markdown table.

## Features
- Baseline vs PR plan comparison (`infracost breakdown` + `infracost diff`)
- Monthly / daily / hourly cost table
- Emoji direction (increase / decrease / no change)
- Resilient parsing + fallback if diff JSON lacks past totals
- Idempotent PR comment updates via marker
- Optional author ping + extra mentions
- Currency flag in headline

## Inputs
| Name | Required | Default | Description |
|------|----------|---------|-------------|
| working_dir | yes | — | Directory containing PR `tfplan.json` |
| base_tfplan_path | yes | — | Absolute path to baseline `tfplan.json` |
| currency | no | USD | Currency code |
| ping_author | no | true | Prepend PR author mention |
| mention_handles | no | (empty) | Additional space or @ separated handles |
| infracost_version | no | latest | Infracost CLI version |
| comment_marker | no | <!-- infracost-comment --> | Marker for updates |

Environment variable required: `INFRACOST_API_KEY`.


## Example Workflow
```yaml
name: Cost Diff
on:
  pull_request:
    paths:
      - infra/**
permissions:
  contents: read
  pull-requests: write
jobs:
  cost:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.9.8
      - name: Baseline plan
        run: |
          terraform -chdir=infra plan -out=base.bin
          terraform -chdir=infra show -json base.bin > base.tfplan.json
      - name: PR plan
        run: |
          terraform -chdir=infra plan -out=pr.bin
          terraform -chdir=infra show -json pr.bin > infra/tfplan.json
      - name: Infracost Core
        uses: faviaitsolutionad/infracost-core@v1.1.0
        with:
          working_dir: infra
          base_tfplan_path: ${{ github.workspace }}/base.tfplan.json
          currency: USD
          mention_handles: "@cloud-team"
        env:
          INFRACOST_API_KEY: ${{ secrets.INFRACOST_API_KEY }}
