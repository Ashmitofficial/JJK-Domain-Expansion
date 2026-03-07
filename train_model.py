import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import tensorflow as tf
from tensorflow.keras import layers, models

# 1. Load the Data
data = pd.read_csv('domain_landmarks.csv', header=None)

# 2. Split Features (X) and Labels (y)
# X = all 126 coordinate columns | y = the last column (the name of the sign)
X = data.iloc[:, :-1].values
y = data.iloc[:, -1].values

# 3. Encode the Labels (Convert 'gojo' to 0, 'sukuna' to 1, etc.)
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)
num_classes = len(np.unique(y_encoded))

# 4. Split into Training and Testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42)

# 5. Build the Neural Network Architecture
model = models.Sequential([
    layers.Input(shape=(126,)),  # Our 126 landmarks
    layers.Dense(64, activation='relu'),
    layers.Dropout(0.2), # Prevents the model from "cheating" or memorizing
    layers.Dense(32, activation='relu'),
    layers.Dense(num_classes, activation='softmax') # Output layer: gives probabilities
])

# 6. Compile and Train
model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])

print("Training the Domain Expansion Model...")
model.fit(X_train, y_train, epochs=50, batch_size=32, validation_data=(X_test, y_test))

# 7. Save the Model and the Label Encoder classes
model.save('domain_model.h5')
np.save('classes.npy', label_encoder.classes_)

print("Success! Model saved as 'domain_model.h5'")