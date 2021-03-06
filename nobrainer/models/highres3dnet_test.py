"""Tests for HighRes3DNet."""

import numpy as np
import tensorflow as tf

import nobrainer


def test_meshnet():
    shape = (1, 10, 10, 10)
    X = np.random.rand(*shape, 1).astype(np.float32)
    y = np.random.randint(0, 9, size=(shape), dtype=np.int32)
    dset_fn = lambda: tf.data.Dataset.from_tensors((X, y))

    estimator = nobrainer.models.HighRes3DNet(
        n_classes=10, optimizer='Adam', learning_rate=0.001)
    estimator.train(input_fn=dset_fn)

    # With optimizer object.
    optimizer = tf.train.AdagradOptimizer(learning_rate=0.001)
    estimator = nobrainer.models.HighRes3DNet(
        n_classes=10, optimizer=optimizer, learning_rate=0.001)
    estimator.train(input_fn=dset_fn)
