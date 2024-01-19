import numpy
import pandas as pd


def get_subbands():
    freqs_df = pd.DataFrame(numpy.arange(902.3, 915.0, 0.2), columns=['freq'])
    # create Channel from Index and shift it to a column
    freqs_df.index.name = 'channel'
    freqs_df = freqs_df.reset_index()

    freqs_df['subband'] = freqs_df.apply(lambda row: int((row.freq - 902.3)/0.2) // 8 + 1, axis=1)
    # set data type to string
    # round to 1 decimal place
    freqs_df['freq'] = freqs_df['freq'].round(1).astype(str)

    freqs_df = freqs_df.set_index('freq')
    return freqs_df
