import sys

import h5py
import numpy as np

import nobrainer

HDF_PATH = "/om/user/jakubk/nobrainer-data-zero_one_range.h5"

DT_T1 = np.float32
DT_APARCASEG = np.int32


def remove_empty_slices(mask_arr, other_arr):
    """Return `mask_arr` and `other_arr` with empty blocks in `mask_arr`
    removed.
    """
    nobrainer.util._check_shapes_equal(mask_arr, other_arr)
    mask = mask_arr.any(axis=(1, 2, 3))
    return (
        mask_arr[mask, Ellipsis],
        other_arr[mask, Ellipsis],
    )


class HdfSinker:
    """Object to initialize and append data to HDF5 file. Kwargs are for
    h5py dataset creation.
    """
    def __init__(self, path, data_info, overwrite=False, **kwargs):
        self.path = path
        self.data_info = data_info
        self.overwrite = overwrite

        if not overwrite:
            import os
            if os.path.isfile(path):
                raise FileExistsError(
                    "File already exists. Use overwrite=True to overwrite."
                )

        with h5py.File(self.path, 'w') as fp:
            for (d, bs, dt) in data_info:
                fp.create_dataset(
                    d, dtype=dt, shape=(0, *bs), maxshape=(None, *bs), **kwargs
                )

    def append(self, data, dataset):
        """Append data to HDF5 dataset, and return indices of appended items.
        """
        # https://stackoverflow.com/a/25656175/5666087

        with h5py.File(self.path, 'a') as fp:
            original_len = fp[dataset].shape[0]
            n_new_items = original_len + data.shape[0]
            fp[dataset].resize(n_new_items, axis=0)
            fp[dataset][-data.shape[0]:] = data
            return (original_len, n_new_items)


def add_one_triple(sink, fp_t1, fp_aparcaseg):
    """Add blocks of t1 and aparcaseg volumes to H5 file in `sink`."""
    try:
        t1 = nobrainer.io.load_volume(fp_t1, dtype=DT_T1)
        aparcaseg = nobrainer.io.load_volume(fp_aparcaseg, dtype=DT_APARCASEG)
    except Exception:
        print("++ Error reading files")
        print(fp_t1)
        print(fp_aparcaseg)
        return

    # for block_type in (32, 64, 128):
    for block_type in (64, 128):
        block_shape = (block_type, ) * 3
        dset_pre = "/{}-iso".format(block_type)

        t1_ = nobrainer.preprocessing.normalize_zero_one(t1).astype(DT_T1)
        t1_ = nobrainer.io.as_blocks(t1_, block_shape)
        aparcaseg_ = nobrainer.io.as_blocks(aparcaseg, block_shape)
        aparcaseg_, t1_ = remove_empty_slices(aparcaseg_, t1_)

        sink.append(t1_, dset_pre + '/t1')
        sink.append(aparcaseg_, dset_pre + '/aparcaseg')


if __name__ == '__main__':

    dset_blocksh_dt = (
       #  ('/32-iso/t1', (32, 32, 32), DT_T1),
       #  ('/32-iso/aparcaseg', (32, 32, 32), DT_APARCASEG),
        ('/64-iso/t1', (64, 64, 64), DT_T1),
        ('/64-iso/aparcaseg', (64, 64, 64), DT_APARCASEG),
        ('/128-iso/t1', (128, 128, 128), DT_T1),
        ('/128-iso/aparcaseg', (128, 128, 128), DT_APARCASEG),
    )

    sinker = HdfSinker(HDF_PATH, dset_blocksh_dt, compression='lzf')

    files = nobrainer.io.read_csv(
        '/om2/user/jakubk/openmind-surface-data/file-lists/'
        'master_file_list_aparcaseg.csv'
    )

    for filepath_t1, filepath_aparcaseg in files:
        print(filepath_t1, filepath_aparcaseg)
        try:
            add_one_triple(
                sinker, fp_t1=filepath_t1, fp_aparcaseg=filepath_aparcaseg
            )
        except Exception:
            print("++ Error processing files")
            print(filepath_t1)
            raise
            print(filepath_aparcaseg)
        sys.stdout.flush()
