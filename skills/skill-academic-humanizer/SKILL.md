---
name: skill-academic-humanizer
version: 1.0.0
description: |
  Extends blader/humanizer with 11 academic-specific AI-writing patterns. 
  Research papers have unique AI tells that general text doesn't. 
  This skill detects and removes them.
license: MIT
compatibility: opencode
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
---

# Academic Humanizer: Research Paper AI Pattern Detection

This skill extends the base Humanizer (30 patterns) with 11 academic-specific patterns. Use in combination with the base Humanizer for 41 total patterns.

## ACADEMIC PATTERNS (#31-41)

### 31. "State-of-the-Art" Inflation

**Problem**: AI writing uses "state-of-the-art" as a generic booster for any method, even ones that are clearly not SOTA.

**Before**: 
> Our method achieves state-of-the-art performance on all benchmarks.

**After**:
> Our method outperforms the previous best published result on ImageNet by 1.2% (top-1 accuracy).

### 32. "To the Best of Our Knowledge" Overuse

**Problem**: This phrase appears in AI papers 3-5x more frequently than in human-written papers. Used to hedge every single novel claim instead of reserved for genuinely surprising findings.

**Before**:
> To the best of our knowledge, this is the first application of transformers to protein folding. To the best of our knowledge, our method achieves the highest accuracy on CASP15.

**After**:
> We are not aware of prior work applying transformers to this specific protein folding task.

### 33. "Further Research Is Needed" Filler

**Problem**: The most generic conclusion in AI-generated papers. Human papers specify what research and why.

**Before**:
> Further research is needed to fully understand the implications of these findings.

**After**:
> Longitudinal studies with clinical populations are needed to determine whether the 12% improvement we observed in laboratory settings generalizes to real-world treatment conditions.

### 34. "Recent Advances" Vagueness

**Problem**: AI papers open with "Recent advances in X" as a vague placeholder instead of citing specific work.

**Before**:
> Recent advances in deep learning have revolutionized natural language processing.

**After**:
> Since 2023, three research groups have applied transformer-based architectures to this problem: Devlin et al. showed BERT improved GLUE scores by 7%, Liu et al. demonstrated RoBERTa matched human performance on SQuAD, and Yang et al. achieved 91% on SuperGLUE with XLNet.

### 35. Formulaic Related Work

**Problem**: The "Smith et al. (2020) investigated... Jones et al. (2021) explored... Lee et al. (2022) studied..." pattern is an obvious AI tell because it lists papers by citation, not by theme.

**Before**:
> Smith et al. (2020) investigated the use of GANs for image generation. Jones et al. (2021) explored using VAEs for the same task. Lee et al. (2022) studied diffusion models for image synthesis.

**After**:
> Three main families of generative models have been applied to image synthesis: GANs (Smith 2020), VAEs (Jones 2021), and diffusion models (Lee 2022). Diffusion models currently achieve the highest FID scores across standard benchmarks.

### 36. "Table/Figure Shows" Without Interpretation

**Problem**: AI papers dump the reader at a table/figure without explaining what to see.

**Before**:
> Table 3 shows the results of our experiments.

**After**:
> Table 3 shows that Method A outperforms Method B by 12% (p<0.01) on the held-out test set, consistent with the hypothesis that attention mechanisms help capture long-range dependencies. However, Method B was 3x faster at inference.

### 37. "Despite These Limitations" Formula

**Problem**: The "Despite these limitations, our work represents..." construction is a template, not an honest assessment.

**Before**:
> Despite these limitations, our work represents a significant step forward in understanding neural network optimization.

**After**:
> The main limitation of our study is the small sample size (n=30), which means the observed 5% improvement may not generalize. We address this by providing bootstrap confidence intervals that account for the sample variance.

### 38. "In This Paper, We" Overuse

**Problem**: AI papers start every section with this construction. Human writers vary their openings.

**Before**:
> In this paper, we propose a new method for... In this paper, we show that... In this paper, we demonstrate...

**After**:
> We propose a new method for... Our experiments show that... The results demonstrate...

### 39. Self-Citation Promotion

**Problem**: AI tools over-cite the current authors' previous work to inflate citation counts, often on tangentially relevant papers.

**Before**:
> Similar approaches were explored in our prior work (Smith 2022, Smith 2023, Smith 2024) which established the foundations for the current study.

**After**:
> Our prior work established the foundational architecture (Smith 2022). The current study extends this by...

### 40. Citation Stacking

**Problem**: Dumping 5-15 citations at once to appear comprehensive. Human writers cite selectively.

**Before**:
> Deep learning has been widely studied [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15].

**After**:
> Deep learning has been widely studied, with surveys by Goodfellow (2016) and LeCun (2015) providing comprehensive overviews.

### 41. "This Paper Proposes/Presents/Introduces" as Opener

**Problem**: This is the most common first sentence in AI-generated papers.

**Before**:
> This paper proposes a novel architecture for neural machine translation based on sparse attention mechanisms.

**After**:
> Sparse attention mechanisms reduce the computational cost of transformer models from O(n²) to O(n log n). We show that this reduction does not come at the cost of translation quality.

## DETECTION GUIDANCE

### What NOT to flag in academic writing

- **Legitimate use of technical terminology**: "groundbreaking" is fine when describing an actual breakthrough. "Pivotal" is fine when describing an actual pivot point. Context matters.
- **Standard academic phrases in moderation**: "To the best of our knowledge" once in a paper is fine. Three times is a tell.
- **Formatting requirements**: Conference templates often require bold headings, title case, and specific structures. These are template-driven, not AI-driven.
- **Co-author contributions**: If multiple humans contributed sections, writing style may vary legitimately.

### What IS always a tell

- **Pattern clusters**: one em dash is nothing. Three em dashes + rule of three + synonym cycling + "further research is needed" = AI generated.
- **Uniform sentence length**: human writing naturally varies.
- **Every paragraph ends with a "broader significance" claim**: "This finding has implications for..." after every single paragraph.
- **No hedging at all**: real academic writing has nuanced uncertainty.
- **Perfect transitions between every paragraph**: humans leave some jumps.
