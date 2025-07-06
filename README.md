# FinOps Toolkit: AWS Cost and Usage

Welcome to the **FinOps Toolkit**—the only toolkit that helps you understand your AWS bill without the need for a PhD in hieroglyphics, a stiff drink, or a séance. This repository contains scripts to explore, analyse, and (hopefully) enjoy your AWS Cost and Usage data (for now), all from the comfort of your terminal.

## What Is This?

A growing collection of Python scripts that use the AWS CLI to pull cost and usage data from your AWS account. The toolkit is designed to help you slice and dice your cloud spend by service, account, or tag, with enough flexibility to satisfy even the most demanding bean counter.

Unlike cobbling together your own scripts in the dead of night, or surrendering to the tyranny of yet another SaaS tool, the FinOps Toolkit aims for the happy middle ground: standardised, collaborative, and open—yet infinitely adaptable.

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

## Arguments

- `--granularity`: hourly, daily, or monthly (required)
- `--interval`: day, week, month, quarter, semester, year (optional)
- `--include-today`: include today in the interval (optional)
- `--group`: SERVICE, LINKED_ACCOUNT, or TAG (default: SERVICE)
- `--tag-key`: Tag key to group by (required if grouping by TAG)
- `--output-format`: csv or json (default: csv)

## Example: Group by Tag

```bash
python aws/cost-and-usage.py --granularity daily --group TAG --tag-key Environment --output-format json
```

## Roadmap

This toolkit is just getting started. Over time, expect a growing suite of scripts that work together—each one a finely tuned instrument in the orchestra of FinOps. The goal: make implementing FinOps more standard than rolling your own, yet more flexible than being shackled to a tool that thinks “customisation” means changing the logo.

## Troubleshooting

- If you see errors about AWS CLI, check your credentials and permissions.
- If you see only zeros, it’s either a good day, or you’ve filtered yourself into oblivion.
- For any other issues, raise an issue or consult your nearest rubber duck.

## License

MIT License. Use, fork, and share. Just don’t blame us if your cloud bill still gives you nightmares.

## Contributing

Pull requests, witty comments, and bug reports are all welcome. If you can make cloud billing funnier, you’re hired (in spirit).

---

*Because understanding your AWS bill shouldn’t require a séance, a therapist, or a second mortgage.*
