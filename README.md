# LLM assessment

[Four-page experiment report](LLM_Assessment_Report.pdf)

| Folder | Experiment | Recorded evidence |
|---|---|---|
| [task1-qlora](task1-qlora) | Convert English task requests to five-field JSON | 100 paired predictions, dataset splits, training loss and saved adapter |
| [task2-rag](task2-rag) | Retrieve evidence from 36 Git manuals with NumPy | 15 annotated questions, ranked passages, two chunk sizes and QA examples |
| [task3-quantization](task3-quantization) | Compare F16 and Q4_K_M on CPU | Raw Ollama responses and timings for both settings, scoring code and prompt comparisons |

Each folder includes its own run instructions. GPU memory figures in the PDF are planning estimates. Training, retrieval and inference results come from the saved experiments.

