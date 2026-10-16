# Literature investigation and contribution check

Updated 26 September 2026. This is an initial primary-source review; it is not a systematic review and does not claim complete IEEE Xplore, Scopus, or Web of Science coverage.

## Closely related rice-yield work

De Clercq and Mahdi, *Feasibility of machine learning-based rice yield prediction in India at the district level using climate reanalysis data*, 2024 preprint, studies 247 districts, 19 classical models, and 2001–2020 Kharif data. Its methods describe district aggregation of ERA5 and satellite covariates, monthly features, and a 2019–2020 temporal test. The paper compares all features with earth-observation-only features. These choices motivate stronger spatial summaries, classical baselines and trend checks here. Its task, inputs and test geography differ from our annual historical pilot; its scores cannot be directly ranked against ours. [Primary manuscript](https://arxiv.org/html/2403.07967v1).

The publisher record for *Rice Yield Forecasting Using Hybrid Quantum Deep Learning Model*, Computers 13(8), 191 (2024), DOI 10.3390/computers13080191, establishes that quantum/rice modelling is already an existing topic. The page returned HTTP 429 during this continuation, so a full methodological audit remains pending. Do not infer a novel contribution simply from combining rice yields and quantum terminology. [Publisher page](https://www.mdpi.com/2073-431X/13/8/191).

## Quantum advantage needs a separate argument

Huang et al., *Power of data in quantum machine learning*, Nature Communications 12, 2631 (2021), explains why classical learners can remain competitive even when the generating quantum process is difficult to compute. The paper motivates explicit classical controls and dataset-dependent evidence. Our four-qubit circuit is efficiently simulated exactly; prediction differences in this pilot establish neither a hardware nor computational advantage. [Primary paper](https://www.nature.com/articles/s41467-021-22539-9).

## Candidate contribution to investigate

A transparent study of **failure modes under geographic and temporal shift**, with matched classical controls, interval calibration, feature removal and reproducible source/split records, is more defensible than a high-accuracy quantum model claim. This is a possible direction, not established novelty. The small regional pilot alone does not establish a publishable contribution.

Before drafting a novelty claim, complete a documented search covering quantum kernels for agricultural regression, spatially grouped yield estimation, trend-only controls and calibration under geographic shift. Record databases, search strings, dates, inclusion rules and any unavailable full texts. Check the closest studies' units, feature timing, split geography, tuning budgets, source overlap and hardware/simulator distinction.

## Submission prerequisites

Preserve negative findings. Report development decisions and every final evaluation. Obtain adequate external or expanded geographic evidence, outcome-definition review and source redistribution terms. Then select a venue by subject fit and actual contribution. Author identity, affiliations, contributions, conflicts, funding and submission declarations must be supplied or confirmed by the authors; they cannot be inferred.

IEEE author policy links for the later submission review: [author responsibilities](https://journals.ieeeauthorcenter.ieee.org/become-an-ieee-journal-author/publishing-ethics/author-responsibilities/), [submission and peer-review policies](https://journals.ieeeauthorcenter.ieee.org/become-an-ieee-journal-author/publishing-ethics/guidelines-and-policies/submission-and-peer-review-policies/). No manuscript has been submitted.

## Continuation scan — 26 September 2026

This targeted web search used queries for quantum crop-yield prediction, quantum rice forecasting, and Indian district-level rice prediction. It was a discovery scan, not a reproducible database search; record and run database-specific searches before making any novelty claim.

- De Clercq and Mahdi's 2024 preprint already studies Kharif rice yield across 247 Indian districts for 2001–2020, using 19 classical models with climate and satellite inputs and an interactive dashboard. Its stated task and geography overlap broadly with this project. The present pilot differs in source period, annual label, small regional coverage, exact simulator, and emphasis on geographic/time holdouts, but the paper means the contribution cannot be framed as the first Indian district rice-yield model or dashboard. A full comparison of source versions, split design, and code is still required. [Primary manuscript](https://arxiv.org/abs/2403.07967).
- Setiadi et al. (2024) already propose a hybrid quantum/deep-learning rice-forecasting model using a Bi-LSTM, quantum feature processing, and XGBoost, evaluated with a classical quantum simulator. The publisher reports an R² close to 1; that number is not comparable with this pilot without matching units, dataset, split, and leakage checks. Quantum processing combined with rice-yield prediction is therefore not itself a novel claim. [Primary article](https://www.mdpi.com/2073-431X/13/8/191).
- Abdel-Aty et al. (2026) report a quantum-ensemble crop-yield regression study. Its methods table identifies a Kaggle crop-yield dataset, Qiskit Aer running on a classical CPU, and 10-fold cross-validation. The reported scores cannot be compared numerically with the present pilot because source records, target units, preprocessing, split grouping, and independent geographic/temporal validation are not established as equivalent. This further rules out a broad “first quantum crop-yield regression” claim. [Primary article](https://www.frontiersin.org/journals/sustainable-food-systems/articles/10.3389/fsufs.2026.1827152/full).

### Implication for the paper

The literature does not establish novelty for quantum crop prediction, rice-plus-quantum modelling, Indian district rice yield modelling, or a yield dashboard by themselves. A narrower contribution may remain in a carefully documented, split-safe evaluation of where simulated quantum kernels fail or differ from matched classical controls under geographic and temporal shift. That contribution is not established yet: the current dataset is small, the exact ICAR CSV is not an independent test source, and the prior India study's split protocol still needs a close audit. Avoid venue selection and submission claims until a systematic search and source audit are completed.
