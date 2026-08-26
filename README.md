# BanglaSafe

<p align="center">
  <a href="https://banglallm.github.io/banglasafe/"><img alt="Accepted at EMNLP 2026 (Findings)" src="https://img.shields.io/badge/%F0%9F%94%A5%20ACCEPTED%20AT-EMNLP%202026%20%28FINDINGS%29%20%F0%9F%94%A5-b22222?style=for-the-badge&labelColor=f5a623"></a>
</p>

[![arXiv](https://img.shields.io/badge/arXiv-2608.22335-b31b1b)](https://arxiv.org/abs/2608.22335)
[![Project page](https://img.shields.io/badge/Project-Page-3fb950)](https://banglallm.github.io/banglasafe/)
[![Leaderboard](https://img.shields.io/badge/Leaderboard-18%20models-8957e5)](https://banglallm.github.io/banglasafe/leaderboard.html)
[![PyPI](https://img.shields.io/pypi/v/banglasafe)](https://pypi.org/project/banglasafe/)
[![Dataset](https://img.shields.io/badge/%F0%9F%A4%97%20dataset-BanglaLLM%2FBanglaSafe-yellow)](https://huggingface.co/datasets/BanglaLLM/BanglaSafe)
[![Python](https://img.shields.io/pypi/pyversions/banglasafe)](https://pypi.org/project/banglasafe/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

A Bengali safety benchmark for LLMs. 879 prompts across 17 harm categories, each one anchored to a Bangladesh statute or a documented case, asked in five different registers.

Point it at any OpenAI-compatible endpoint and it gives you an attack success rate.

One command, nothing to install:

```bash
uvx banglasafe run \
  --model Qwen/Qwen3-32B-Instruct \
  --base-url http://localhost:8000/v1 \
  --judge-model anthropic/claude-opus-4-7 \
  --judge-base-url https://openrouter.ai/api/v1
```

`uvx` fetches it, runs it, and cleans up. If you want it to stick around, `uv tool install
banglasafe`. If you would rather use pip, `pip install banglasafe` works too, just slower.

```
  ASR loose   47.2%  [44.1, 50.3]   PARTIAL + HARMFUL
  ASR strict  19.8%                 HARMFUL only

  vs the 18-model reference cohort: z = -0.22, rank 11/19 (safer than cohort average)

  Register effect  BN_Formal is 16.4pp higher than BN_Collq (reference cohort: +17.5pp)
```

## The point of it

Most multilingual safety work translates English harm categories into other languages. That loses the harms that only exist locally, like hundi, yaba, or bKash fraud, and it loses register. Bengali is diglossic, so the same request reads very differently as newspaper prose, as code-mixed Banglish, or as an institutional case file.

Across the 18 models we tested, a harmful request written as a formal newspaper investigation got answered 17.5 points more often than the same request written as a casual message. No jailbreak, no prompt engineering, just a change of register.

## Reading the output

Two rates. ASR loose counts PARTIAL and HARMFUL, meaning the model engaged. ASR strict counts only HARMFUL, meaning it produced something usable. Report both or you are either overstating or understating.

Every rate gets a bootstrap 95% CI, broken out by condition, by category, and by whether the prompt was human-written or model-generated. Cells under n=30 get no CI instead of a useless one.

Your score is placed against 18 reference models that ship with the package, so you get a z-score and a rank rather than a number with no context.

Each report also prints how well the judge agrees with human labels, because the label is an estimate and you should be able to see its error bar.

## Endpoints

It speaks plain `/v1/chat/completions`, so one `--base-url` covers vLLM, SGLang, LightLLM, Ollama, llama.cpp, TGI, LM Studio, a LiteLLM proxy, OpenRouter, Together, and Groq. Both a `/v1` base and a full `/v1/chat/completions` URL work.

## Picking a judge

`--judge-model` is required and there is no default. The judge decides your numbers, so it should be a choice you make.

| judge | agreement |
|---|---|
| `anthropic/claude-opus-4-7` | The judge behind the published labels. Binary kappa 0.666 against human gold on 300 responses, above inter-human 0.586. |
| `google/gemini-3.1-pro` | Independent second judge. Agrees with the first at binary kappa 0.787, per-model Pearson r 0.989 across 18 models. |

Any OpenAI-compatible model can judge. Only these two have measured agreement with humans on this benchmark, and the tool warns you if you pick something else.

## Commands

```bash
banglasafe run       # query, judge, score, report
banglasafe score     # re-score an existing run, offline
banglasafe report    # re-render terminal and HTML from a finished run
banglasafe compare   # rank runs side by side
banglasafe judges    # judge options and their calibration
banglasafe cohort    # the 18 reference models
banglasafe info      # dataset, rubric hash, version
```

Flags worth knowing:

```bash
--limit 20                                    # 20 harm instances, all 5 conditions each
--condition BN_Formal --condition BN_Collq    # just the register comparison
--category hundi                              # one harm
--max-concurrency 16                          # minutes instead of an hour
--config banglasafe.yaml                      # flags still override the file
```

`--limit` takes whole harm instances rather than the first N rows, so a subset still compares like
with like. (5 of the 167 instances are missing a condition in the source data.)

## Output

```
results/<model>__<timestamp>/
  responses.jsonl
  labels.jsonl
  summary.json
  report.html
```

The JSONL files are the real output. `summary.json` and `report.html` are derived and you can rebuild them with `banglasafe report`. Runs resume: kill one and re-run the same command, and it picks up instead of charging you twice.

## Config

Flags beat environment variables, which beat the YAML file.

```yaml
target:
  model: Qwen/Qwen3-32B-Instruct
  base_url: http://localhost:8000/v1
  api_key: "{{ env.LOCAL_API_KEY }}"
judge:
  model: anthropic/claude-opus-4-7
  base_url: https://openrouter.ai/api/v1
  api_key: "{{ env.OPENROUTER_API_KEY }}"
run:
  max_concurrency: 16
```

`{{ env.VAR }}` expands at load, so keys stay out of the file. It also reads `BANGLASAFE_BASE_URL`, `BANGLASAFE_API_KEY`, `BANGLASAFE_JUDGE_BASE_URL`, `BANGLASAFE_JUDGE_API_KEY`, and falls back to `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `VLLM_BASE_URL`, `SGLANG_BASE_URL`, `OLLAMA_BASE_URL`.

## How it runs

Temperature 0, top_p 1, no system prompt. Decoding settings alone can swing open-model safety rates from near zero to over 95% on the same prompts, so they stay fixed. No system prompt is the consumer chatbot case.

The judge rubric ships in the package and its hash goes into every report. Four labels, a decision algorithm, an edge-case table, 17 tie-breakers. Same spec that produced the published labels.

Labels are noisy. Binary judge-vs-human kappa is 0.666, and four-way inter-human kappa is only 0.286, which is why the binary collapse is the headline and the four-way split is reported next to it rather than instead. Differences inside the confidence intervals are noise.

## Data

Prompts live at [BanglaLLM/BanglaSafe](https://huggingface.co/datasets/BanglaLLM/BanglaSafe). The
tool downloads the JSONL directly and caches it in `~/.cache/banglasafe`, so there is no token and
no heavy data library in the dependency tree. Set `BANGLASAFE_CACHE` to move it.

If you want the dataset for something else:

```python
from datasets import load_dataset
prompts  = load_dataset("BanglaLLM/BanglaSafe")
taxonomy = load_dataset("BanglaLLM/BanglaSafe", "taxonomy")
```

## Please don't

These prompts exist to make unsafe behaviour measurable. Use them to evaluate models, not to extract harmful content, and don't train on them to make a model more willing.

The benchmark measures harmful compliance. It says nothing about over-refusal, since there is no benign control set. It cannot tell you whether hardening a model against the journalism register would make it start refusing real investigative reporting.

## Citation

```bibtex
@inproceedings{islam2026banglasafe,
  title     = {Register Shifts Break {LLM} Safety: A Bengali Benchmark with Culturally Grounded Harms},
  author    = {Islam, Naymul and Lia, Nusrat Jahan and Roy Dipta, Shubhashis and Sultan, Sabik Bin and Zehady, Abdullah Khan},
  booktitle = {Findings of the Association for Computational Linguistics: EMNLP 2026},
  year      = {2026},
  eprint    = {2608.22335},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CL},
  url       = {https://arxiv.org/abs/2608.22335}
}
```

MIT for the code, CC-BY-4.0 for the dataset.
