# Production model artifacts

These files are trusted `joblib` artifacts copied from `research/models` for
the standalone analysis service. They use artifact schema 3 and were created
with Python 3.14.3, NumPy 2.5.3, pandas 3.0.6, scikit-learn 1.9.1,
CatBoost 1.2.10, and joblib 1.6.0.

The service validates the schema, fixed eleven-feature order, and exact model
runtime versions before accepting traffic. The legacy iron artifact with PR-AUC
0.7612 is intentionally excluded because it was serialized with
scikit-learn 1.7.2 and has no runtime metadata.

| Task | Artifact | SHA-256 |
|---|---|---|
| iron deficiency | `latent_deficiency_iron_deficiency_test_pr_auc_0.7582.joblib` | `3647b3b03f89866d2cc6f8fa4d5b91fc87ede28cc045b997718e4c8dc58aca1f` |
| B12 deficiency | `B12_deficiency_no_anemia_B12_deficiency_test_pr_auc_0.5746.joblib` | `d932e52cfab947c05e4f10c3b9d97949d0c9d94d5ac46f8ca3cddc2339f8ae09` |
| folate deficiency | `folate_deficiency_no_anemia_folate_deficiency_test_pr_auc_0.2857.joblib` | `13d195d0292c3581d68ae80c1ca4928ac007cd6c709e42c11afc28d53baa4548` |
| B6 deficiency | `B6_deficiency_B6_deficiency_test_pr_auc_0.4817.joblib` | `8ff5ff28dc18a96e711aca5cc14feae7a8cacab856de2012d064f92cef81a5cc` |
| copper deficiency | `copper_deficiency_copper_deficiency_test_pr_auc_0.4444.joblib` | `2fea58be14697a6b9d09f460bc146c2bcbf469c348c338b95eb450ce80cbb90f` |
