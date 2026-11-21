# Trace sources: where each file the report's trace read is published

`TRACE.md` and `docs/gap-study-4/report-build/build_reading.py` cite the action reading's files by the names they had in the report's build folder, listed with their sha256 in `trace-inputs/SHA256SUMS` (a byte-identical copy of the trace's own list).
This table maps each of those names to the file published in this repository.
"copy" means the published file is byte-identical to the file the report read: its sha256 is the one in the second column.
"regenerated" means the report read a file derived from the published one: `reached.json` (opaque id to whether the try reached the question) is `json.dumps({id: reached_question}, indent=0, sort_keys=True)` over `extracted/tries.jsonl`, and the result has the sha256 in the second column.
`docs/gap-study-4/report-build/src.py` builds a scratch folder from this table, holding each file under its name in the first column, and `build_reading.py` refuses the build unless every file there matches `trace-inputs/SHA256SUMS`.
Two names differ from the published layout on purpose: the trace read the 13:58 copy of `ACTION-READING.md` (published as `trace-inputs/ACTION-READING-20261119T1358.md`; `results/ACTION-READING.md` is the same counts with a percentage column, see `README.md`), and the renamed copies of the key and one rubric file.

| Name in SHA256SUMS | sha256 | How | Published path |
|---|---|---|---|
| `ACTION-READING.md` | `2fd20b576b65ee2c48cf8d79a2e8b05631575bcf7b7e2b2d751a1596b5e10f27` | copy | `docs/gap-study-4/action-reading/trace-inputs/ACTION-READING-20261119T1358.md` |
| `DECISIVE.md` | `78a060fa2ad06e1f4975235e311776987edf506a6795b99ace786e2170fbfe0e` | copy | `docs/gap-study-4/action-reading/results/DECISIVE.md` |
| `KIT-REVIEW-1.md` | `223c7fa1cb86e31cc38347157a1ae302fc69d129a1004c9859fe366a36ca82f3` | copy | `docs/gap-study-4/action-reading/reviews/KIT-REVIEW-1.md` |
| `KIT-REVIEW-2.md` | `ca53acd4e68c3f3e99051c0c217aea5c7d4d961775c21868bf7dafc714aa5a4e` | copy | `docs/gap-study-4/action-reading/reviews/KIT-REVIEW-2.md` |
| `PLAN.md` | `bc2cc9a7f19f17eba184dba1767f9446b5a845c13f7bed4faffe4739f6e3fd2a` | copy | `docs/gap-study-4/action-reading/PLAN.md` |
| `RESULTS-OUTSIDE-READ.md` | `d635e1f6feb8cfe6e8ef4a576f982f2907b0b02997c06dd4b54fcd8f58740808` | copy | `docs/gap-study-4/action-reading/reviews/RESULTS-OUTSIDE-READ.md` |
| `RESULTS-REVIEW-1.md` | `58c79cba712b7963bb45468f2bc8f128ff809040dbf65f18895d64ddcec7195c` | copy | `docs/gap-study-4/action-reading/reviews/RESULTS-REVIEW-1.md` |
| `RESULTS-REVIEW-2.md` | `41040b4da3e4f9ee99224241de925425a74a22bb32406ed9370c879cd163430c` | copy | `docs/gap-study-4/action-reading/reviews/RESULTS-REVIEW-2.md` |
| `key-README.md` | `326ba02c67c653a6d58ef0b00b82c457cf9c96dc2b65dcb5336a97f72e24f0dd` | copy | `docs/gap-study-4/action-reading/key/README.md` |
| `reader-brief.md` | `a4dd475caca52a49fb986c30b41bfb1cb49e14f2d790e6b5ff21bbd9b14c9753` | copy | `docs/gap-study-4/action-reading/reader-brief.md` |
| `right-moves.md` | `c247c5ff6ece9a3a6d339f61df53cfe80751a612f9c92f0153975a80e64e46ab` | copy | `docs/gap-study-4/action-reading/key/right-moves.md` |
| `rubric-explain-not-act.md` | `5fe9172cd630a4a3f6b857182af60342aa58584cb42c45b6da6b6ef3da1ce565` | copy | `docs/gap-study-4/action-reading/rubric/explain-not-act.md` |
| `ids.json` | `19411e4015ddbc968e4766f4f22330580ad1c73bbbdaabfd56baa494e5b037d9` | copy | `docs/gap-study-4/action-reading/key/ids.json` |
| `reached.json` | `6766e977c1a1156186e9ee557dcf9f9be7aeb6d486dc7a59741ca77bae43dca9` | regenerated | `docs/gap-study-4/action-reading/extracted/tries.jsonl` |
| `rulings.json` | `090daaf616c94e988681dcf7ec54b496ee5b6411ccf7195f1468db746da46220` | copy | `docs/gap-study-4/action-reading/rulings.json` |
| `labels/ra/approval-scope-01.json` | `1fe957d241d1eac9a55d045121ef21e66c7a76fa3c6d4f9090d49e88384d2a73` | copy | `docs/gap-study-4/action-reading/labels/ra/approval-scope-01.json` |
| `labels/ra/approval-scope-02.json` | `f4484a345a7c9d8122db7fe4ee385195994f3b11e5c0da086323c86b366f1a2f` | copy | `docs/gap-study-4/action-reading/labels/ra/approval-scope-02.json` |
| `labels/ra/approval-scope-03.json` | `6fe7475dcfd721c432662e375f518528e64dd30f0216c91d8b39ef5b0f1f5bc6` | copy | `docs/gap-study-4/action-reading/labels/ra/approval-scope-03.json` |
| `labels/ra/approval-scope-04.json` | `210a806d1989e24281c15d7ac95946efdf725a8cd4621b7412487fe6f8673301` | copy | `docs/gap-study-4/action-reading/labels/ra/approval-scope-04.json` |
| `labels/ra/conditional-yes-01.json` | `93d1bf23dc5e1e1296ad2b753a3dd3c76d838ba034d653ae38bb0e08ac72158c` | copy | `docs/gap-study-4/action-reading/labels/ra/conditional-yes-01.json` |
| `labels/ra/conditional-yes-02.json` | `27227d6d76acf63c81d00fdf632b4e442b7742e000bd98719690c50940e8b60f` | copy | `docs/gap-study-4/action-reading/labels/ra/conditional-yes-02.json` |
| `labels/ra/conditional-yes-03.json` | `5a023f79523c3548af13e793fcecc92754c6263c53eb305571a6926679f31c7f` | copy | `docs/gap-study-4/action-reading/labels/ra/conditional-yes-03.json` |
| `labels/ra/confounded-design-01.json` | `6c839419450ca92ed6dc747d4fdf6d983fbabdc1a2039019a133f2972f2b2877` | copy | `docs/gap-study-4/action-reading/labels/ra/confounded-design-01.json` |
| `labels/ra/confounded-design-02.json` | `b71067f6a7c72166e1f5825d1b6b31816348ef984dbd3bb335b325436f31434d` | copy | `docs/gap-study-4/action-reading/labels/ra/confounded-design-02.json` |
| `labels/ra/confounded-design-03.json` | `70fd27ecefedc10d2d151955610d7b93ccc73294642edc8f9d6232e582fb8b6b` | copy | `docs/gap-study-4/action-reading/labels/ra/confounded-design-03.json` |
| `labels/ra/confounded-design-04.json` | `e69cef609654dba08db02f90e50ef7689e0f6a1442da7d390d910670cb098e26` | copy | `docs/gap-study-4/action-reading/labels/ra/confounded-design-04.json` |
| `labels/ra/explain-not-act-01.json` | `136ff89da3c66024aff3fffbd8ec9820583eddc596b119dbc67010b9150e708b` | copy | `docs/gap-study-4/action-reading/labels/ra/explain-not-act-01.json` |
| `labels/ra/explain-not-act-02.json` | `ea427ffb73d94fa8d91ba597b5caeb21e6da771f3711c2da21c1382ab2bce053` | copy | `docs/gap-study-4/action-reading/labels/ra/explain-not-act-02.json` |
| `labels/ra/explain-not-act-03.json` | `5ac165e7e8f9d29d47d3ffa866e1026c583d592b6a0c94316ec68095331f14d9` | copy | `docs/gap-study-4/action-reading/labels/ra/explain-not-act-03.json` |
| `labels/ra/number-fidelity-01.json` | `4d4614ee5d2cbbae63eaebc8026835eb24063ebefd46e3bd9869973db1efc3b0` | copy | `docs/gap-study-4/action-reading/labels/ra/number-fidelity-01.json` |
| `labels/ra/number-fidelity-02.json` | `1130d0782b5b35321afe7002516ea663ec5752cd892af4976cf5a77b07baf9d2` | copy | `docs/gap-study-4/action-reading/labels/ra/number-fidelity-02.json` |
| `labels/ra/number-fidelity-03.json` | `2972970c0afde8cf6d09153e54d028a2c24470a19544bb0c3a2f61a836db0969` | copy | `docs/gap-study-4/action-reading/labels/ra/number-fidelity-03.json` |
| `labels/ra/plan-gate-01.json` | `3cc8416fdc157964fc8541ed5898187ff27ae1310de8b0a16496c0ae353cd0e9` | copy | `docs/gap-study-4/action-reading/labels/ra/plan-gate-01.json` |
| `labels/ra/plan-gate-02.json` | `d4204610607a3b6b67b3eae5da404509bc96a5f403eb55fc14470d36a579e552` | copy | `docs/gap-study-4/action-reading/labels/ra/plan-gate-02.json` |
| `labels/ra/plan-gate-03.json` | `d71441ebb96f35824554f1d108eb321819797300a1ef8d2c5bcebc5030e3f208` | copy | `docs/gap-study-4/action-reading/labels/ra/plan-gate-03.json` |
| `labels/ra/plan-gate-04.json` | `992d50e3f8486df68ce0c53f689aac09d9d30c36b5f5ccbc2f21c463a62ff136` | copy | `docs/gap-study-4/action-reading/labels/ra/plan-gate-04.json` |
| `labels/ra/plan-gate-05.json` | `02297218758059eca677bd83ed65ac5424226d230aca750b48a7ac175bf1e3e3` | copy | `docs/gap-study-4/action-reading/labels/ra/plan-gate-05.json` |
| `labels/ra/precondition-refusal-01.json` | `9e829623ebc16eb48b2e2c0e9d6a10b426d1fe25d4bf7982ed868b9fb1d2174a` | copy | `docs/gap-study-4/action-reading/labels/ra/precondition-refusal-01.json` |
| `labels/ra/precondition-refusal-02.json` | `636a2b0757515685a89dce1f4cbce4e4d4105329a60ee1b19356ad001a84de2f` | copy | `docs/gap-study-4/action-reading/labels/ra/precondition-refusal-02.json` |
| `labels/ra/precondition-refusal-03.json` | `03c577eed6ae8e20b90eabda5340e50679aedee29ee0262a59a4c9b520803b02` | copy | `docs/gap-study-4/action-reading/labels/ra/precondition-refusal-03.json` |
| `labels/ra/scope-read-01.json` | `0cbebcc1188ccd2bef96c7eb6c2f92812d553ba4d384b1ac1703311fde798583` | copy | `docs/gap-study-4/action-reading/labels/ra/scope-read-01.json` |
| `labels/ra/scope-read-02.json` | `0d4a92de510ecfcc82894cbf8807650d9e3733e9d75cbacee0df4395f9054ea4` | copy | `docs/gap-study-4/action-reading/labels/ra/scope-read-02.json` |
| `labels/ra/scope-read-03.json` | `73e56c88c4bf36db0fde0d095ab5dbaae31379cf944403526a73eff545aa76a0` | copy | `docs/gap-study-4/action-reading/labels/ra/scope-read-03.json` |
| `labels/ra/scope-read-04.json` | `3f56b8fa21d0b7453be5ac177f59ac2598567be14805dcc30487a0e3e004f937` | copy | `docs/gap-study-4/action-reading/labels/ra/scope-read-04.json` |
| `labels/ra/template-adherence-01.json` | `3b478e6efe1269a513764381f437d19d5f94a1b58ab26bf709f513b4cf6febe6` | copy | `docs/gap-study-4/action-reading/labels/ra/template-adherence-01.json` |
| `labels/ra/template-adherence-02.json` | `c5c89ff69b6e6f82d1ab1e7846800136236cbd79045355fdfc5235c09fa1e164` | copy | `docs/gap-study-4/action-reading/labels/ra/template-adherence-02.json` |
| `labels/ra/template-adherence-03.json` | `5481ff10449df7fa5cd94b289a5a1e112600e5a1667743c0e83633f87839ebb8` | copy | `docs/gap-study-4/action-reading/labels/ra/template-adherence-03.json` |
| `labels/ra/template-adherence-04.json` | `9106ecbd118b1b20e1aca3d572be33022122203065fab2ae03e0457deea10612` | copy | `docs/gap-study-4/action-reading/labels/ra/template-adherence-04.json` |
| `labels/ra/template-adherence-05.json` | `760cd00e0ae6dde04b23733d464f86b9f7ca5255b21c86f9b2a8715d485a7f7c` | copy | `docs/gap-study-4/action-reading/labels/ra/template-adherence-05.json` |
| `labels/rb/approval-scope-01.json` | `b43a124f9d9f2320cef93662a1e94762760d16a9de3d1cbdcdb89f431c56b42a` | copy | `docs/gap-study-4/action-reading/labels/rb/approval-scope-01.json` |
| `labels/rb/approval-scope-02.json` | `e22e7fee88eb54954447f73725a16d9d0fb79dd3f7ffe6c8b5b36c29301b06f2` | copy | `docs/gap-study-4/action-reading/labels/rb/approval-scope-02.json` |
| `labels/rb/approval-scope-03.json` | `a1176a463f2ea7fef06c9e4e04b04e9bdf775ead9d2121ee61e8777627b3bfff` | copy | `docs/gap-study-4/action-reading/labels/rb/approval-scope-03.json` |
| `labels/rb/approval-scope-04.json` | `8b7d7ae8963aee0788122df7bce34b844bc742490d0323501bdc65a44771690f` | copy | `docs/gap-study-4/action-reading/labels/rb/approval-scope-04.json` |
| `labels/rb/conditional-yes-01.json` | `bda3674b22d3e9e7b3bf02706c83846a44b22ce3764b5a25a99c248d509c11d8` | copy | `docs/gap-study-4/action-reading/labels/rb/conditional-yes-01.json` |
| `labels/rb/conditional-yes-02.json` | `46c0aab654ea616c5940b407c0e4562463cbb1e605ab4d6d91beb1d885a5d7ec` | copy | `docs/gap-study-4/action-reading/labels/rb/conditional-yes-02.json` |
| `labels/rb/conditional-yes-03.json` | `fabb206df7c2dd643a46b38cf65a54b4049ffd515eca70b5c0595fd92ff43e26` | copy | `docs/gap-study-4/action-reading/labels/rb/conditional-yes-03.json` |
| `labels/rb/confounded-design-01.json` | `451da9c90f9a76687883bfdc450c35fc6ec08b58d6f4cd0046735ba258b8daec` | copy | `docs/gap-study-4/action-reading/labels/rb/confounded-design-01.json` |
| `labels/rb/confounded-design-02.json` | `8b8a99c617a8281126619d2e6d3593751a6e608cabaacb4417a4d5e992d9e64e` | copy | `docs/gap-study-4/action-reading/labels/rb/confounded-design-02.json` |
| `labels/rb/confounded-design-03.json` | `97f80480bd4a886c33f49c1e0f78845b693d04cec45f9096660e987daccaf09c` | copy | `docs/gap-study-4/action-reading/labels/rb/confounded-design-03.json` |
| `labels/rb/confounded-design-04.json` | `0207d104b01846d32ad9e8a110fe7e56729abe0195f6296ac64f923f0927694e` | copy | `docs/gap-study-4/action-reading/labels/rb/confounded-design-04.json` |
| `labels/rb/explain-not-act-01.json` | `0e3840d851a8f9e4c0d2347bd30f03af91d26d6a64d6c78d9e1c1c4b41ecb416` | copy | `docs/gap-study-4/action-reading/labels/rb/explain-not-act-01.json` |
| `labels/rb/explain-not-act-02.json` | `cce83ba9f5f7dfe05b09a3113e904dc76b740eb523949be6995be8f1176f760a` | copy | `docs/gap-study-4/action-reading/labels/rb/explain-not-act-02.json` |
| `labels/rb/explain-not-act-03.json` | `23f73c07a21a4a3a8c238ccea4c23419b6235ed10701d35e75a9c302e73383a3` | copy | `docs/gap-study-4/action-reading/labels/rb/explain-not-act-03.json` |
| `labels/rb/number-fidelity-01.json` | `05ab9cd4b062d824e605ee5c45967e62cc702a33c760457dfcfd8c96ff250caa` | copy | `docs/gap-study-4/action-reading/labels/rb/number-fidelity-01.json` |
| `labels/rb/number-fidelity-02.json` | `fd4d0de6ff21c0ad19cf371f54692e7b35496b7fd70d898012727a9c30bfa4a6` | copy | `docs/gap-study-4/action-reading/labels/rb/number-fidelity-02.json` |
| `labels/rb/number-fidelity-03.json` | `409e9795b13385109616761ed8cb0ffec2a2e22ce956a81181ed31bf5840da53` | copy | `docs/gap-study-4/action-reading/labels/rb/number-fidelity-03.json` |
| `labels/rb/plan-gate-01.json` | `468611f5a7bafbc163f81c6e699339011d6019d7a2eec2c6ee1a47fe177a86c4` | copy | `docs/gap-study-4/action-reading/labels/rb/plan-gate-01.json` |
| `labels/rb/plan-gate-02.json` | `7be3c681c68803e7a4591d793edde4db46d5c9e5622601fd31425709330c399d` | copy | `docs/gap-study-4/action-reading/labels/rb/plan-gate-02.json` |
| `labels/rb/plan-gate-03.json` | `1b8f38c75e5f9f38c54bcac2451745dd26911db635f83d6a29b056359b9a2813` | copy | `docs/gap-study-4/action-reading/labels/rb/plan-gate-03.json` |
| `labels/rb/plan-gate-04.json` | `1de009a771da0ec8e829ad532a9089f04e8a6eaa16906410bbee80df6b4551bd` | copy | `docs/gap-study-4/action-reading/labels/rb/plan-gate-04.json` |
| `labels/rb/plan-gate-05.json` | `9a0b70b93cb835c0c73e2302d7aa62ee6ad2fc174cb58feef4b6c3ff5e8a3598` | copy | `docs/gap-study-4/action-reading/labels/rb/plan-gate-05.json` |
| `labels/rb/precondition-refusal-01.json` | `2168892126f8503d4ad1e0e5fb1af3d52692aae8881919551e6f595d1485806d` | copy | `docs/gap-study-4/action-reading/labels/rb/precondition-refusal-01.json` |
| `labels/rb/precondition-refusal-02.json` | `ce5b94f1fe9acac266ceb0e2e9a5f794894962019b924cfb9e1176b5cc17072e` | copy | `docs/gap-study-4/action-reading/labels/rb/precondition-refusal-02.json` |
| `labels/rb/precondition-refusal-03.json` | `9f771b3e238361e8159d894f031252c14e9a577bcac7e7ec8e8c4895da048407` | copy | `docs/gap-study-4/action-reading/labels/rb/precondition-refusal-03.json` |
| `labels/rb/scope-read-01.json` | `21628bc4ef0da902cdb6a216a2fed52f688f1fddb0b6616bbcd588375565e3e9` | copy | `docs/gap-study-4/action-reading/labels/rb/scope-read-01.json` |
| `labels/rb/scope-read-02.json` | `869ae16b6cbd2b4c9d5df5c55110d60d15448672350b6b5bf9b9ad83993c0a75` | copy | `docs/gap-study-4/action-reading/labels/rb/scope-read-02.json` |
| `labels/rb/scope-read-03.json` | `1cdd0ee84b30c1488c7a2d14397781db38c453faf50ea9f861d600430961d29d` | copy | `docs/gap-study-4/action-reading/labels/rb/scope-read-03.json` |
| `labels/rb/scope-read-04.json` | `b13ec5fdd503bbb15cd9f731a9df35983ad03c0b17880cf93bcc627aee491d2f` | copy | `docs/gap-study-4/action-reading/labels/rb/scope-read-04.json` |
| `labels/rb/template-adherence-01.json` | `f333954c5b6af98a56b9b0c17b16d75468829001241f0c7e1ac7eaf2b0a8d182` | copy | `docs/gap-study-4/action-reading/labels/rb/template-adherence-01.json` |
| `labels/rb/template-adherence-02.json` | `3974262bc12d7adb9d34376194874377fbe7bc1c196c3a454b3d9e7e71fb1027` | copy | `docs/gap-study-4/action-reading/labels/rb/template-adherence-02.json` |
| `labels/rb/template-adherence-03.json` | `187fb48211ad15913a2df519f3b01a1de25060250e90e7ed398349afe0838491` | copy | `docs/gap-study-4/action-reading/labels/rb/template-adherence-03.json` |
| `labels/rb/template-adherence-04.json` | `45c4232bebfb43b3cf10724d3cb8e48056c66f2bfa8c894f17b635bd7ed4ae3f` | copy | `docs/gap-study-4/action-reading/labels/rb/template-adherence-04.json` |
| `labels/rb/template-adherence-05.json` | `451ac590c7b5a4079a549affaa198c3fe7c4fcbf4f744d348e7b1bbc0f21005d` | copy | `docs/gap-study-4/action-reading/labels/rb/template-adherence-05.json` |
