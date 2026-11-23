# Data provenance and integrity notice

**The dataset in `02_Datasets/raw_dataset.csv` is SYNTHETIC.**

It was generated locally with `03_Source_Code/generate_raw_dataset.py` using `numpy.random.default_rng(42)` on Python 3.14.5, then written once. The generator is included so the raw file can be reproduced exactly.

This was done at the explicit request of the project owner, overriding the original brief rule that raw data be user-supplied and not generated. Consequences that must be disclosed in the report and any oral defense:

- The dataset does not describe real students. Findings demonstrate the **analysis pipeline and methodology**, not real-world educational effects.
- Causal or generalizable claims about real students are **not** supported.
- The synthetic data-generating process is a limitation, not a source of authority.

The raw file is treated as immutable from this point on. All cleaning writes to `02_Datasets/cleaned_dataset.csv`, and every action is recorded in `02_Datasets/cleaning_log.csv`.

Topic used: Student Academic Performance Analysis (default from the brief; change if a different topic is required).
