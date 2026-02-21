# Reaction Source Pack (Open-source references)

This folder tracks credible open datasets/papers for empathy-oriented short responses.

## Referenced open sources
1. **EmpatheticDialogues** (Rashkin et al., ACL 2019)
   - Paper: https://aclanthology.org/P19-1534/
   - HF dataset: https://huggingface.co/datasets/empathetic_dialogues
2. **DailyDialog** (Li et al., IJCNLP 2017)
   - Paper: https://aclanthology.org/I17-1099/
   - HF dataset: https://huggingface.co/datasets/daily_dialog
3. **GoEmotions** (Demszky et al., ACL 2020)
   - Paper: https://aclanthology.org/2020.acl-main.372/
   - HF dataset: https://huggingface.co/datasets/go_emotions

## What is included here
- `reaction_source_index.json`: source metadata and intended usage
- `reaction_candidates_v01.json`: curated short reaction candidates grouped by positive/negative/neutral/ambiguous/bridge

## Notes
- These are **curated fast-lane snippets** informed by open datasets/literature style.
- Do not directly copy long dialogue turns; keep short and latency-safe.
