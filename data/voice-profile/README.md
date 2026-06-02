# Voice Profile

The voice profile teaches the Writer agents to match **your** writing style at the sentence level — vocabulary, sentence length, paragraph rhythm, formality, and citation habits.

Without a voice profile, the Writer uses a generic academic style. With one, it produces text indistinguishable from your published work.

## How it works

1. Place 2–3 paragraphs of your published or polished writing in a `.txt` file here.
2. Run `agent profile extract` (or the pipeline will extract it automatically).
3. The system generates a `voice-profile.json` with metrics:
   - Average sentence length
   - Vocabulary distribution (unique words / total words)
   - Passive vs. active voice ratio
   - Common transition patterns
   - Paragraph structure (avg paragraphs per section, sentences per paragraph)
4. Writers use this profile as a generation constraint. The Style Auditor verifies consistency against it.

## Provided files

| File | Purpose |
|------|---------|
| `sample-writing.txt` | 2 paragraphs of academic writing (sample source) |
| `sample-profile.json` | Extracted voice profile from the sample |
| `README.md` | This file |

## Creating your own

Replace `sample-writing.txt` with your own text, then delete `sample-profile.json` — the pipeline will regenerate it. For best results:

- Use 2–3 paragraphs of your **published** writing (paper, blog post, thesis)
- Mix sections if possible (intro paragraph + methods paragraph + conclusion paragraph)
- Avoid AI-generated text (the system will detect inconsistency)
- Update the profile when your writing style evolves
