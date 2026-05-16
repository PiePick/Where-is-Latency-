---
tags:
- setfit
- sentence-transformers
- text-classification
- generated_from_setfit_trainer
widget:
- text: and four cars /
- text: C So, yeah, /
- text: '# Yeah, /'
- text: Okay, /
- text: I'm surprised to hear that. /
metrics:
- accuracy
pipeline_tag: text-classification
library_name: setfit
inference: true
base_model: sentence-transformers/all-MiniLM-L6-v2
---

# SetFit with sentence-transformers/all-MiniLM-L6-v2

This is a [SetFit](https://github.com/huggingface/setfit) model that can be used for Text Classification. This SetFit model uses [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) as the Sentence Transformer embedding model. A [LogisticRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html) instance is used for classification.

The model has been trained using an efficient few-shot learning technique that involves:

1. Fine-tuning a [Sentence Transformer](https://www.sbert.net) with contrastive learning.
2. Training a classification head with features from the fine-tuned Sentence Transformer.

## Model Details

### Model Description
- **Model Type:** SetFit
- **Sentence Transformer body:** [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- **Classification head:** a [LogisticRegression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html) instance
- **Maximum Sequence Length:** 256 tokens
- **Number of Classes:** 6 classes
<!-- - **Training Dataset:** [Unknown](https://huggingface.co/datasets/unknown) -->
<!-- - **Language:** Unknown -->
<!-- - **License:** Unknown -->

### Model Sources

- **Repository:** [SetFit on GitHub](https://github.com/huggingface/setfit)
- **Paper:** [Efficient Few-Shot Learning Without Prompts](https://arxiv.org/abs/2209.11055)
- **Blogpost:** [SetFit: Efficient Few-Shot Learning Without Prompts](https://huggingface.co/blog/setfit)

### Model Labels
| Label       | Examples                                                                                                                                                                                                            |
|:------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| ACKNOWLEDGE | <ul><li>'F Oh, F oh. /'</li><li>'F Oh, really. /'</li><li>'# D You know # D like, yeah, /'</li></ul>                                                                                                                |
| DIRECTIVE   | <ul><li>'C But go ahead, /'</li><li>'D Well, if our time is up we can quit. /'</li><li>"don't tell that to a native Texan though, /"</li></ul>                                                                      |
| EXPRESSIVE  | <ul><li>'Hope you like you it. /'</li><li>"I'm glad to find there's another reasonable person in Garland. /"</li><li>'Hi. /'</li></ul>                                                                              |
| REJECT      | <ul><li>'No, /'</li><li>'D Well, not really, /'</li><li>'No, /'</li></ul>                                                                                                                                           |
| QUESTION    | <ul><li>'Is there a lot of sand in, - /'</li><li>'Are you at work? /'</li><li>"D Well, you weren't charging gold and silver were you? /"</li></ul>                                                                  |
| INFORM      | <ul><li>'C and then a lot of other stuff we just wait until it comes out on tape. /'</li><li>"she's very old fashioned. /"</li><li>'C and he, F uh, saved himself in the, in the, in the process also. /'</li></ul> |

## Uses

### Direct Use for Inference

First install the SetFit library:

```bash
pip install setfit
```

Then you can load this model and run inference.

```python
from setfit import SetFitModel

# Download from the 🤗 Hub
model = SetFitModel.from_pretrained("setfit_model_id")
# Run inference
preds = model("Okay, /")
```

<!--
### Downstream Use

*List how someone could finetune this model on their own dataset.*
-->

<!--
### Out-of-Scope Use

*List how the model may foreseeably be misused and address what users ought not to do with the model.*
-->

<!--
## Bias, Risks and Limitations

*What are the known or foreseeable issues stemming from this model? You could also flag here known failure cases or weaknesses of the model.*
-->

<!--
### Recommendations

*What are recommendations with respect to the foreseeable issues? For example, filtering explicit content.*
-->

## Training Details

### Training Set Metrics
| Training set | Min | Median | Max |
|:-------------|:----|:-------|:----|
| Word count   | 1   | 7.2731 | 30  |

| Label       | Training Sample Count |
|:------------|:----------------------|
| QUESTION    | 180                   |
| INFORM      | 180                   |
| ACKNOWLEDGE | 180                   |
| DIRECTIVE   | 180                   |
| EXPRESSIVE  | 180                   |
| REJECT      | 180                   |

### Training Hyperparameters
- batch_size: (16, 16)
- num_epochs: (1, 1)
- max_steps: -1
- sampling_strategy: oversampling
- num_iterations: 5
- body_learning_rate: (2e-05, 1e-05)
- head_learning_rate: 0.01
- loss: CosineSimilarityLoss
- distance_metric: cosine_distance
- margin: 0.25
- end_to_end: False
- use_amp: False
- warmup_proportion: 0.1
- l2_weight: 0.01
- seed: 42
- eval_max_steps: -1
- load_best_model_at_end: False

### Training Results
| Epoch  | Step | Training Loss | Validation Loss |
|:------:|:----:|:-------------:|:---------------:|
| 0.0030 | 1    | 0.2655        | -               |
| 0.1479 | 50   | 0.2595        | -               |
| 0.2959 | 100  | 0.2016        | -               |
| 0.4438 | 150  | 0.1758        | -               |
| 0.5917 | 200  | 0.1582        | -               |
| 0.7396 | 250  | 0.145         | -               |
| 0.8876 | 300  | 0.1331        | -               |

### Framework Versions
- Python: 3.12.3
- SetFit: 1.1.3
- Sentence Transformers: 5.5.0
- Transformers: 4.57.6
- PyTorch: 2.10.0+cu128
- Datasets: 4.8.5
- Tokenizers: 0.22.2

## Citation

### BibTeX
```bibtex
@article{https://doi.org/10.48550/arxiv.2209.11055,
    doi = {10.48550/ARXIV.2209.11055},
    url = {https://arxiv.org/abs/2209.11055},
    author = {Tunstall, Lewis and Reimers, Nils and Jo, Unso Eun Seo and Bates, Luke and Korat, Daniel and Wasserblat, Moshe and Pereg, Oren},
    keywords = {Computation and Language (cs.CL), FOS: Computer and information sciences, FOS: Computer and information sciences},
    title = {Efficient Few-Shot Learning Without Prompts},
    publisher = {arXiv},
    year = {2022},
    copyright = {Creative Commons Attribution 4.0 International}
}
```

<!--
## Glossary

*Clearly define terms in order to be accessible across audiences.*
-->

<!--
## Model Card Authors

*Lists the people who create the model card, providing recognition and accountability for the detailed work that goes into its construction.*
-->

<!--
## Model Card Contact

*Provides a way for people who have updates to the Model Card, suggestions, or questions, to contact the Model Card authors.*
-->