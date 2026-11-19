# QLoRA for five-field task extraction

[Training and evaluation notebook on Colab](https://colab.research.google.com/drive/1iZxY4DLy3OHX_W-PSVg_jst0CvaD-iJz). The original run used a Tesla T4. The pinned model revision, package versions and training settings are in metrics.json. The data directory contains the generator and all three splits. task1_dataset.zip is the archive identified by the SHA-256 in metrics.json.

Run `python score.py` to independently parse both saved prediction files and reproduce the test scores with the Python standard library. The entire response must parse as JSON and equal the expected object. An adapter checkpoint and tokenizer files are in adapter/. Load them against the base revision specified in metrics.json. failures.json and analysis.txt give the error analysis.

