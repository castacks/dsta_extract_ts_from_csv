
import argparse
import os
import pandas as pd
import re
import sys

def create_dir_from_filename(fn):
    d = os.path.dirname(fn)
    os.makedirs(d, exist_ok=True)

def read_csv(fn):
    # The CSV file should have a header like
    # /camera_image0,/camera_image1,/camera_image2
    return pd.read_csv(fn, header=0)

def extract_timestamp(digits):
    assert len(digits) == 19, \
        f'The length of the digits is not 19. digits = {digits}. '
    
    return digits[:10], digits[10:]

def process_column(col):
    # A column is a sequence of strings like
    # /data/01_PillarRoom_15ms/images_2/1688567270696679671.png
    # We need to extract the time stamp embedded in the file name.

    pattern = r'(\d+)\.png$'
    search = re.compile(pattern)

    list_sec = []
    list_nsec = []

    for fn in col:
        m = search.search(fn)

        if m:
            # Extract the time stamp.
            sec, nsec = extract_timestamp(m.group(1))
            list_sec.append(sec)
            list_nsec.append(nsec)
        else:
            raise ValueError('The filename does not match the pattern. The filename is {fn}')

    return list_sec, list_nsec

def save_sec_nsec(fn, list_sec, list_nsec):
    # Construct a dataframe.
    df = pd.DataFrame({'sec': list_sec, 'nsec': list_nsec})

    # Write a CSV file.
    df.to_csv(fn, index=False, columns=['sec', 'nsec'])

def handle_args():
    parser = argparse.ArgumentParser(description='Extract time stamps from a csv file. ')

    parser.add_argument('--in_file', type=str, required=True,
                        help='The input file. ')
    parser.add_argument('--out_file', type=str, required=True,
                        help='The output file. ')
    parser.add_argument('--ref', type=str, default='/camera_image2',
                        help='The reference camera that time stamps are extracted frome. ')
    
    return parser.parse_args()

def main():
    # Handle the arguments.
    args = handle_args()

    # Create the output directory.
    create_dir_from_filename(args.out_file)

    # Read the input file.
    df = read_csv(args.in_file)

    # Get the column.
    col = df[args.ref]

    # Process the column.
    list_sec, list_nsec = process_column(col)

    # Save the results.
    save_sec_nsec(args.out_file, list_sec, list_nsec)

    print(f'Timestamps extracted to {args.out_file}. ')

    return 0

if __name__ == '__main__':
    sys.exit(main())