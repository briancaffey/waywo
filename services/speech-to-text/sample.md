How to Use this Model
The model is available for use in the NeMo Framework, and can be used as a pre-trained checkpoint for inference or for fine-tuning on another dataset.

Loading the Model
import nemo.collections.asr as nemo_asr
asr_model = nemo_asr.models.ASRModel.from_pretrained(model_name="nvidia/nemotron-speech-streaming-en-0.6b")

Streaming Inference
You can use the cache-aware streaming inference script from NeMo - NeMo/examples/asr/asr_cache_aware_streaming/speech_to_text_cache_aware_streaming_infer.py

```
cd NeMo
python examples/asr/asr_cache_aware_streaming/speech_to_text_cache_aware_streaming_infer.py \
    model_path=<model_path> \
    dataset_manifest=<dataset_manifest> \
    batch_size=<batch_size> \
    att_context_size="[70,13]" \ #set the second value to the desired right context from {0,1,6,13}
    output_path=<output_folder>
```

You can also run streaming inference through the pipeline method, which uses NeMo/examples/asr/conf/asr_streaming_inference/cache_aware_rnnt.yaml configuration file to build end‑to‑end workflows with punctuation and capitalization (PnC), inverse text normalization (ITN), and translation support.

The full url for this file is here: [https://github.com/NVIDIA-NeMo/NeMo/blob/main/examples/asr/asr_cache_aware_streaming/speech_to_text_cache_aware_streaming_infer.py](https://github.com/NVIDIA-NeMo/NeMo/blob/main/examples/asr/asr_cache_aware_streaming/speech_to_text_cache_aware_streaming_infer.py)

```python
from nemo.collections.asr.inference.factory.pipeline_builder import PipelineBuilder
from omegaconf import OmegaConf

# Path to the cache aware config file downloaded from above link
cfg_path = 'cache_aware_rnnt.yaml'
cfg = OmegaConf.load(cfg_path)

# Pass the paths of all the audio files for inferencing
audios = ['/path/to/your/audio.wav']

# Create the pipeline object and run inference
pipeline = PipelineBuilder.build_pipeline(cfg)
output = pipeline.run(audios)

# Print the output
for entry in output:
  print(entry['text'])
```