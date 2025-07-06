# FinOps Toolkit: AWS Cost and Usage

Welcome to the **FinOps Toolkit**—the only toolkit that helps you understand your AWS bill without the need for a PhD in hieroglyphics, a stiff drink, or a séance. This repository contains scripts to explore, analyse, and (hopefully) enjoy your AWS Cost and Usage data (for now), all from the comfort of your terminal.

## What Is This?

A growing collection of Python scripts that use the AWS CLI to pull cost and usage data from your AWS account. The toolkit is designed to help you slice and dice your cloud spend by service, account, or tag, with enough flexibility to satisfy even the most demanding bean counter.

Unlike cobbling together your own scripts in the dead of night, or surrendering to the tyranny of yet another SaaS tool, the FinOps Toolkit aims for the happy middle ground: standardised, collaborative, and open, yet infinitely adaptable.

## Features

- **Flexible granularity:** Choose between hourly, daily, or monthly data. (Because sometimes you want to know exactly when your budget went up in smoke.)
- **Custom intervals:** Report by day, week, month, quarter, semester, or year. Or just pick “today” if you like living on the edge.
- **Group by:** Service, linked account, or tag. Group therapy for your cloud costs.
- **Output formats:** CSV or JSON, always delivered to standard out, so you can redirect, pipe, or just stare at the numbers in awe.
- **Extensible:** New scripts will be added over time, working together to make FinOps implementation more standardised than DIY, yet far more flexible than any boxed-in tool.
- **No nonsense:** No web dashboards, no vendor lock-in, and absolutely no blockchain.

## Quickstart

1. **Install Requirements**

   - Python 3.7+
   - AWS CLI configured with permissions for Cost Explorer
   - Your favourite terminal

2. **Run the script**

   ```bash
   python aws/cost-and-usage.py --granularity daily --interval month --group SERVICE --output-format csv
   ```

   For more options, try:

   ```bash
   python aws/cost-and-usage.py --help
   ```

3. **Sample Output**

   Redirect CSV output to a file, or pipe it to your favourite spreadsheet tool:

   ```bash
   python aws/cost-and-usage.py --granularity monthly --group LINKED_ACCOUNT > costs.csv
   ```

## Arguments and Examples

Below are all the flags, with examples to make your testing as painless as possible.

### `--granularity`
Granularity of the data: `hourly`, `daily`, or `monthly` (required).

```bash
python aws/cost-and-usage.py --granularity hourly --group SERVICE
python aws/cost-and-usage.py --granularity daily --group SERVICE
python aws/cost-and-usage.py --granularity monthly --group SERVICE
```

### `--interval`
Interval to report: `day`, `week`, `month`, `quarter`, `semester`, or `year` (optional).

```bash
python aws/cost-and-usage.py --granularity daily --interval week --group SERVICE
python aws/cost-and-usage.py --granularity monthly --interval year --group SERVICE
```

### `--include-today`
Include today in the interval (optional; because sometimes you want to see the damage as it happens).

```bash
python aws/cost-and-usage.py --granularity daily --interval week --include-today --group SERVICE
```

### `--group`
Group costs by `SERVICE`, `LINKED_ACCOUNT`, or `TAG` (default: `SERVICE`).

```bash
python aws/cost-and-usage.py --granularity daily --group SERVICE
python aws/cost-and-usage.py --granularity daily --group LINKED_ACCOUNT
python aws/cost-and-usage.py --granularity daily --group TAG --tag-key Environment
```

### `--tag-key`
Tag key to group by (required if grouping by TAG). Choose your favourite tag, or your least favourite.

```bash
python aws/cost-and-usage.py --granularity daily --group TAG --tag-key Environment
python aws/cost-and-usage.py --granularity monthly --group TAG --tag-key Owner
```

### `--output-format`
Output format: `csv` or `json` (default: `csv`). For those who like their data raw, or at least semi-structured.

```bash
python aws/cost-and-usage.py --granularity daily --output-format csv
python aws/cost-and-usage.py --granularity daily --output-format json
```

### Combining Flags

Because you are a power user (or at least aspire to be):

```bash
python aws/cost-and-usage.py --granularity hourly --interval day --include-today --group TAG --tag-key Project --output-format json
```

### Redirecting Output

Send output to a file, or pipe it into oblivion:

```bash
python aws/cost-and-usage.py --granularity monthly --group SERVICE --output-format csv > my-costs.csv
python aws/cost-and-usage.py --granularity daily --group TAG --tag-key Owner --output-format json > tag-costs.json
```

## Roadmap

This toolkit is just getting started. Over time, expect a growing suite of scripts that work together—each one a finely tuned instrument in the orchestra of FinOps. The goal: make implementing FinOps more standard than rolling your own, yet more flexible than being shackled to a tool that thinks “customisation” means changing the logo.

## Troubleshooting

- If you see errors about AWS CLI, check your credentials, permissions, and whether you have angered the cloud gods.
- If you see only zeros, it’s either a good day, or you’ve filtered yourself into oblivion.
- For any other issues, raise an issue, consult your nearest rubber duck, or take a brisk walk.

## License

MIT License. Use, fork, and share. Just don’t blame us if your cloud bill still gives you nightmares.

## Contributing

Pull requests, witty comments, and bug reports are all welcome. If you can make cloud billing funnier, you’re hired (in spirit).

---

_Because understanding your AWS bill shouldn’t require a séance, a therapist, or a second mortgage._
