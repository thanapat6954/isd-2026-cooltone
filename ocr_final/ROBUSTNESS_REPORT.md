# Robustness Evaluation Report

Generated on 2026-09-20 from the five authoritative Lab 8B databases.

## Authoritative outputs

| Profile | Folder | Credits | Verify | Gold Q&A |
|---|---|---:|---:|---:|
| DSBA coop | `work/lab8b_dsba_coop` | 132 | 7/7 | 30/30 |
| DSBA no-coop | `work/lab8b_dsba_no_coop` | 132 | 7/7 | 30/30 |
| AI | `work/lab8b_ai` | 120 | 7/7 | 30/30 |
| IT coop | `work/lab8b_it_coop` | 129 | 7/7 | 30/30 |
| IT no-coop | `work/lab8b_it_no_coop` | 129 | 7/7 | 30/30 |

All gold evaluations had 100% SQL execution, answer accuracy, citation coverage,
and responses under five seconds. AI and both IT tracks now have their own
30-question answer keys; they are no longer represented only by database checks.

## Held-out Chapter 9-style evaluation

The evaluation uses a separate 12-question set per profile and three repetitions.
The actual Ollama request specifies `temperature: 0.0`. The slices are value,
count, set, and expected-not-found. Result rows, answers, SQL, and citations are
compared across runs for stability.

The original v1 set exposed a shared count-query error and scored 10/12. Those
baseline files remain preserved. After that intent was fixed, the distinct v2
sets were not used to develop further fixes. The current rerun produced:

| Profile | Held-out | Value | Count | Set | None | Stable | Citations | Mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DSBA coop | 12/12 | 6/6 | 2/2 | 2/2 | 2/2 | Yes | 12/12 | 1.023 s |
| DSBA no-coop | 12/12 | 6/6 | 2/2 | 2/2 | 2/2 | Yes | 12/12 | 1.221 s |
| AI | 12/12 | 6/6 | 2/2 | 2/2 | 2/2 | Yes | 12/12 | 1.013 s |
| IT coop | 12/12 | 6/6 | 2/2 | 2/2 | 2/2 | Yes | 12/12 | 1.057 s |
| IT no-coop | 12/12 | 6/6 | 2/2 | 2/2 | 2/2 | Yes | 12/12 | 1.027 s |

Every profile has 100% real-answer recall, 100% expected-not-found accuracy,
100% abstention precision, and zero false abstentions. All 60 first-run questions
were under five seconds.

## OCR comparison

| Profile | Alignment F1 | Thai exact | Thai WER | Credits exact | Category exact | Thai tier |
|---|---:|---:|---:|---:|---:|---|
| DSBA coop | 92.13% | 82.93% | 10.45% | 87.80% | 97.56% | 80–90% |
| DSBA no-coop | 94.4% (n=45) | 80.95% | 27.27% | 88.10% | 100% | 80–90% |
| AI | 91.36% | 97.30% | 2.13% | 100% | 100% | >91% |
| IT coop | 93.20% | 81.25% | 26.79% | 97.92% | 100% | 80–90% |
| IT no-coop | 93.46% | 82.00% | 22.03% | 96.00% | 100% | 80–90% |

DSBA no-coop now has a separate Lab 7B `evaluation.json`, with OCR alignment F1
94.4% over n=45 ground-truth courses. The remaining IT weakness is mainly exact Thai
spelling and mandatory/elective inference. Academic-plan tables do not explicitly mark
every type, so that field should not be presented as pure OCR accuracy without this caveat.

## Re-run

```powershell
.\venv\Scripts\python.exe .\robustness_eval.py --program all --repeats 3
```

Machine-readable combined output is `work/robustness_summary.json`. Detailed
questions and runs are stored in each profile's `robustness/` folder.
