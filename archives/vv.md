Subject: EOD Update: Analysis of the OLMES Evaluation Framework

Today, I conducted an in-depth study of the **OLMES (Open Language Model Evaluation Standard)**, a framework designed to bring scientific rigor and reproducibility to the evaluation of Large Language Models (LLMs). The suite addresses a critical gap in the field: the fact that minor, undocumented variations in prompt formatting can lead to performance swings as high as 80% on a single task.

---

## Key Pillars of the OLMES Framework

The OLMES suite is built on several documented and practical principles to ensure that when we compare two models, the results are actually representative of their capabilities rather than their sensitivity to specific prompts.

### 1. Dual Task Formulation (MCF vs. CF)
One of the most significant findings in the study is the relationship between model strength and task formulation. OLMES recommends evaluating models using both:
*   **Multiple-Choice Formulation (MCF):** The model predicts a label (e.g., "A", "B").
*   **Completion Formulation (CF):** The model's probability for the actual answer text is measured.

The research shows that CF is essential for eliciting a signal from weaker or early-training models, whereas MCF provides a much more accurate assessment for frontier-class models. [Formulation Strategy](https://alphaxiv.org/abs/2406.08446v2?page=7)

### 2. Standardized Probability Normalization
For the Completion Formulation, OLMES removes the guesswork by prescribing specific normalization techniques based on the dataset's nature:
*   **PMI Normalization:** Used for datasets like **ARC-CHALLENGE** and **OpenBookQA** to account for the a priori likelihood of certain words.
*   **Character Normalization:** The standard for most benchmarks like **MMLU** and **HellaSwag** to balance varying answer lengths.
*   **No Normalization:** Reserved for binary tasks like **BoolQ**.

### 3. Curated Few-Shot Prompting
To avoid the noise introduced by random sampling, OLMES uses a fixed, **curated 5-shot approach**. This ensures the prompt includes diverse examples and a balanced distribution of answer labels, providing a stable learning curve for the model. [Few-Shot](https://alphaxiv.org/abs/2406.08446v2?page=5)

---

## Summary of Evaluated Tasks

The framework was tested across 10 core benchmarks. Below is a summary of the standardized settings for a few key tasks:

| Task | Primary Formulation | Recommended Normalization |
| :--- | :--- | :--- |
| **ARC-CHALLENGE** | MCF/CF (Best of) | PMI |
| **MMLU** | MCF/CF (Best of) | Character |
| **BoolQ** | MCF/CF (Best of) | None |
| **HellaSwag** | MCF/CF (Best of) | Character |

## Technical Takeaway
The study highlights that "scientific credibility in AI rests on reproducible and well-considered comparisons." By adopting OLMES, we can ensure our internal benchmarks are directly comparable to external results without the typical ambiguity found in model cards and leaderboards.

> "OLMES provides justified recommendations on all aspects of task setups, such as data sampling, how to format instances, the choice of in-context examples, probability normalization, and task formulation." [OLMES Overview](https://alphaxiv.org/abs/2406.08446v2?page=2)

Please let me know if you would like to dive deeper into any of the specific normalization experiments or the curated prompt examples.