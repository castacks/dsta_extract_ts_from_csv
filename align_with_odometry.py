
import argparse
import bisect
import numpy as np
import os
import pandas as pd
import re
from scipy.spatial.transform import Rotation as R
from scipy.spatial.transform import Slerp
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

def process_video_column(col):
    # A column is a sequence of strings like
    # /data/01_PillarRoom_15ms/images_2/1688567270696679671.png
    # We need to extract the time stamp embedded in the file name.

    pattern = r'(\d+)\.png$'
    search = re.compile(pattern)

    list_ts = []

    for fn in col:
        m = search.search(fn)

        if m:
            # Extract the time stamp.
            list_ts.append(int(m.group(1)))
        else:
            raise ValueError('The filename does not match the pattern. The filename is {fn}')

    return list_ts

def read_csv_video(fn_csv_from_video, ref):
    # Read the CSV file from the video.
    df = read_csv(fn_csv_from_video)

    # Get the column.
    col = df[ref]

    # Process the column.
    return process_video_column(col)

def read_csv_odometry(fn_csv_from_odometry):
    df = read_csv(fn_csv_from_odometry)
    
    # Save the timestamps as a list.
    ts = df['timestamp'].astype(int).to_list()
    
    # Save the rest of the columns as a numpy array.
    pose_table = df.drop(columns=['timestamp'])
    
    return ts, pose_table

def find_closest_indices(list_ref, to_find):
    index_upper = bisect.bisect_left(list_ref, to_find)
    n_ref = len(list_ref)
    
    if index_upper == n_ref:
        return index_upper, index_upper
    elif index_upper == 0:
        return 0, 0
    
    return index_upper - 1, index_upper

def interpolate_quaternions(q0, q1, t):
    """
    Interpolate between two quaternions using Spherical Linear Interpolation (SLERP).
    
    Parameters:
        q0 (numpy.array): The first quaternion [x, y, z, w].
        q1 (numpy.array): The second quaternion [x, y, z, w].
        t (float): Interpolation parameter between 0 and 1.
    
    Returns:
        numpy.array: The interpolated quaternion.
    """
    r0 = R.from_quat(q0)
    r1 = R.from_quat(q1)
    slerp = Slerp( [0, 1], R.concatenate( [ r0, r1 ] ) )
    interpolated_rotation = slerp([t])[0]
    interpolated_quaternion = interpolated_rotation.as_quat()
    return interpolated_quaternion

def interpolate_pose(ts_table, pose_table, ts_in):
    # ts_table is a list of timestamps represented in a long string with digits.
    # pose_table is a pandas dataframe with columns defineds as
    # p_w_b_x, p_w_b_y, p_w_b_z, q_w_b_x, q_w_b_y, q_w_b_z, q_w_b_w.
    # ts_in is a list of timestamps represented in the same way as ts_table.
    # For every timestamp in ts_in, find the closest two timestamps in ts_table. Then interpolate
    # the pose of these two timestamps to get a pose at the timestamp in ts_in.
    
    # Find the lower and upper indices.
    index_lower, index_upper = find_closest_indices(ts_table, ts_in)
    
    if index_lower == index_upper:
        x = pose_table.iloc[index_lower]['p_w_b_x']
        y = pose_table.iloc[index_lower]['p_w_b_y']
        z = pose_table.iloc[index_lower]['p_w_b_z']
        
        q = pose_table.loc[ index_lower, 
                            [ 'q_w_b_x', 'q_w_b_y', 'q_w_b_z', 'q_w_b_w' ] ].values
    else:
        # Find the ratio of the interpolation.
        ts_lower = ts_table[index_lower]
        ts_upper = ts_table[index_upper]
        r = (ts_in - ts_lower) / (ts_upper - ts_lower)
        
        # Interpolate the position.
        x = ( 1 - r ) * pose_table.iloc[index_lower]['p_w_b_x'] + r * pose_table.iloc[index_upper]['p_w_b_x']
        y = ( 1 - r ) * pose_table.iloc[index_lower]['p_w_b_y'] + r * pose_table.iloc[index_upper]['p_w_b_y']
        z = ( 1 - r ) * pose_table.iloc[index_lower]['p_w_b_z'] + r * pose_table.iloc[index_upper]['p_w_b_z']
        
        # Interpolate the orientation.
        q_lower = pose_table.loc[ index_lower, 
                            [ 'q_w_b_x', 'q_w_b_y', 'q_w_b_z', 'q_w_b_w' ] ].values
        
        q_upper = pose_table.loc[ index_upper, 
                            [ 'q_w_b_x', 'q_w_b_y', 'q_w_b_z', 'q_w_b_w' ] ].values
        
        q = interpolate_quaternions(q_lower, q_upper, r)
        
    return np.array([x, y, z]), q
    

def handle_args():
    parser = argparse.ArgumentParser(description='Extract time stamps from a csv file. ')

    parser.add_argument('--csv_from_video', type=str, required=True,
                        help='The CSV file that records the filenames that are extracted from videos. ')
    parser.add_argument('--csv_from_odometry', type=str, required=True,
                        help='The CSV file generated by localization. ')
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

    # Read the CSV file from the video.
    list_ts_video = read_csv_video(args.csv_from_video, args.ref)
    list_ts_odometry, pose_table = read_csv_odometry(args.csv_from_odometry)
    # import ipdb; ipdb.set_trace()
    
    # Create a new list of poses by aligning the timestamps.
    list_int_pos = []
    list_int_quat = []
    for ts_video in list_ts_video:
        pos, quat = interpolate_pose( list_ts_odometry, pose_table, ts_video )
        list_int_pos.append(pos)
        list_int_quat.append(quat)
        
    # Create a new dataframe.
    array_int_pos = np.stack(list_int_pos, axis=0)
    array_int_quat = np.stack(list_int_quat, axis=0)
    
    df_int_pos = pd.DataFrame(array_int_pos, columns=['x', 'y', 'z'])
    df_int_quat = pd.DataFrame(array_int_quat, columns=['qx', 'qy', 'qz', 'qw'])
    df_ts_video = pd.DataFrame(list_ts_video, columns=['timestamp'])

    df = pd.concat([df_ts_video, df_int_pos, df_int_quat], axis=1)

    # Write a CSV file.
    df.to_csv(args.out_file, index=False, columns=['timestamp', 'x', 'y', 'z', 'qx', 'qy', 'qz', 'qw'])

    print(f'Timestamps extracted to {args.out_file}. ')

    return 0

if __name__ == '__main__':
    sys.exit(main())