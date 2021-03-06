#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Example training script."""

import argparse

import h5py
import numpy as np
import tensorflow as tf

import nobrainer
from nobrainer.io import read_mapping
from nobrainer.preprocessing import binarize, preprocess_aparcaseg
from nobrainer.util import iter_hdf5, input_fn_builder

# Data types of labels (x) and features (y).
DT_X = 'float32'
DT_Y = 'int32'
_DT_X_NP = np.dtype(DT_X)
_DT_X_TF = tf.as_dtype(DT_X)
_DT_Y_NP = np.dtype(DT_Y)
_DT_Y_TF = tf.as_dtype(DT_Y)


def train(params):
    """Train estimator."""

    x_dataset = params['xdset']
    y_dataset = params['ydset']

    tf.logging.info(
        'Using features dataset {x} and labels dataset {y}'
        .format(x=x_dataset, y=y_dataset)
    )

    with h5py.File(params['hdf5path'], mode='r') as fp:
        examples_per_epoch = fp[x_dataset].shape[0]
        assert examples_per_epoch == fp[y_dataset].shape[0]

    if params['aparcaseg_mapping']:
        tf.logging.info(
            "Reading mapping file: {}".format(params['aparcaseg_mapping']))
        mapping = read_mapping(params['aparcaseg_mapping'])
    else:
        mapping = None

    def normalizer_aparcaseg(features, labels):
        return features, preprocess_aparcaseg(labels, mapping)

    def normalizer_brainmask(features, labels):
        return features, binarize(labels, threshold=0)

    if params['aparcaseg_mapping'] is not None:
        normalizer = normalizer_aparcaseg
    elif params['brainmask']:
        normalizer = normalizer_brainmask
    else:
        normalizer = None

    def generator_builder():
        """Return a function that returns a generator."""
        return iter_hdf5(
            filepath=params['hdf5path'],
            x_dataset=x_dataset,
            y_dataset=y_dataset,
            x_dtype=_DT_X_NP,
            y_dtype=_DT_Y_NP,
            shuffle=False,
            normalizer=normalizer)

    _output_shapes = (
        (*params['block_shape'], 1),
        params['block_shape'])

    input_fn = input_fn_builder(
        generator=generator_builder,
        output_types=(_DT_X_TF, _DT_Y_TF),
        output_shapes=_output_shapes,
        num_epochs=params['n_epochs'],
        multi_gpu=params['multi_gpu'],
        examples_per_epoch=examples_per_epoch,
        batch_size=params['batch_size'])

    runconfig = tf.estimator.RunConfig(
        save_summary_steps=25,
        save_checkpoints_steps=100,
        keep_checkpoint_max=100)

    model = nobrainer.models.get_estimator(params['model'])(
        n_classes=params['n_classes'],
        optimizer=params['optimizer'],
        learning_rate=params['learning_rate'],
        model_dir=params['model_dir'],
        config=runconfig,
        multi_gpu=params['multi_gpu'])

    model.train(input_fn=input_fn)


def _check_required_keys_exist(params):
    keys = {
        'n_classes', 'model', 'model_dir', 'optimizer', 'learning_rate',
        'batch_size', 'block_shape', 'brainmask', 'aparcaseg_mapping',
        'hdf5path', 'x_dset', 'y_dset', 'multi_gpu', 'n_epochs',
    }
    for key in keys:
        if key not in params:
            raise ValueError("Required key not in parameters: {}".format(key))


def create_parser():
    """Return argument parser."""
    p = argparse.ArgumentParser()
    p.add_argument(
        '-n', '--n-classes', required=True, type=int,
        help="Number of classes to classify")
    p.add_argument(
        '-m', '--model', required=True, choices={'highres3dnet', 'meshnet'},
        help="Model to use")
    p.add_argument(
        '-o', '--optimizer', required=True,
        help="TensorFlow optimizer to use for training")
    p.add_argument(
        '-l', '--learning-rate', required=True, type=float,
        help="Learning rate to use with optimizer for training")
    p.add_argument(
        '-b', '--batch-size', required=True, type=int,
        help=(
            "Number of samples per batch. If `--multi-gpu` is specified, batch"
            " is split across available GPUs."))
    p.add_argument(
        '--block-shape', nargs=3, required=True, type=int,
        help="Height, width, and depth of input data and features.")
    p.add_argument('--hdf5path', required=True, help="Path to input HDF5")
    p.add_argument('--xdset', required=True, help="Features dataset in HDF5")
    p.add_argument('--ydset', required=True, help="Labels dataset in HDF5")
    p.add_argument(
        '-e', '--n-epochs', type=int, default=1,
        help="Number of training epochs")
    p.add_argument(
        '--brainmask', action='store_true',
        help="If specified, binarize labels data")
    p.add_argument(
        '--aparcaseg-mapping',
        help=(
            "Path to CSV mapping file. First column contains original labels,"
            " and second column contains new labels in range [0, n_classes-1]."
            " Header must be included. More than two columns are accepted, but"
            " only the first two columns are used."))
    p.add_argument(
        '--model-dir',
        help=(
            "Directory in which to save model checkpoints. If an existing"
            " directory, will resume training from last checkpoint. If not"
            " specified, will use a temporary directory."))
    p.add_argument(
        '--multi-gpu', action='store_true',
        help=(
            "If specified, train across all available GPUs. Batches are split"
            " across GPUs."))
    return p


def parse_args(args):
    """Return namespace of arguments."""
    parser = create_parser()
    return parser.parse_args(args)


if __name__ == '__main__':
    import sys

    print("USING UP-TO-DATE CODE", flush=True)

    namespace = parse_args(sys.argv[1:])
    params = vars(namespace)

    if params['brainmask'] and params['aparcaseg_mapping']:
        raise ValueError(
            "brainmask and aparcaseg-mapping cannot both be provided.")

    params['block_shape'] = tuple(params['block_shape'])

    train(params)
