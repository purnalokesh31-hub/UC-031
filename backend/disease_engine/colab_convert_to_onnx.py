"""
colab_convert_to_onnx.py
Run this script in Google Colab (free) to convert the PlantVillage model to ONNX.

Steps:
  1. Open https://colab.research.google.com/
  2. Create new notebook
  3. Paste and run the code below
  4. Download 'plant_disease_model.onnx' (~10 MB)
  5. Copy it to: UC-031/backend/disease_engine/plant_disease_model.onnx

=== PASTE THIS INTO GOOGLE COLAB ===

!pip install tf2onnx tensorflow-cpu onnxruntime -q

import urllib.request, os

# Download model
url = "https://huggingface.co/spaces/EcoTensors/CropCare-AI/resolve/main/plant_disease_model.h5"
print("Downloading model...")
urllib.request.urlretrieve(url, "plant_disease_model.h5")
print("Done:", os.path.getsize("plant_disease_model.h5") // 1024, "KB")

# Convert to ONNX
import tensorflow as tf
import tf2onnx

model = tf.keras.models.load_model("plant_disease_model.h5", compile=False)
print("Model loaded. Input:", model.input_shape, "Output:", model.output_shape)

input_sig = [tf.TensorSpec(model.input_shape, tf.float32, name="input")]
onnx_model, _ = tf2onnx.convert.from_keras(model, input_signature=input_sig, opset=13)

import onnx
onnx.save(onnx_model, "plant_disease_model.onnx")
print("ONNX saved:", os.path.getsize("plant_disease_model.onnx") // 1024, "KB")

# Verify
import onnxruntime as ort
sess = ort.InferenceSession("plant_disease_model.onnx")
print("Input:", sess.get_inputs()[0].name, sess.get_inputs()[0].shape)
print("Output:", sess.get_outputs()[0].name, sess.get_outputs()[0].shape)
print("Conversion successful!")

# Download the file from Colab
from google.colab import files
files.download("plant_disease_model.onnx")

=== END COLAB CODE ===

After downloading, place the .onnx file in:
  UC-031/backend/disease_engine/plant_disease_model.onnx

Then restart the backend server:
  cd UC-031/backend
  uvicorn main:app --reload --port 8000

The CropCare AI disease engine will automatically use the ONNX model on Python 3.14.
"""

# This file is documentation only — run the code in Google Colab.
print(__doc__)
