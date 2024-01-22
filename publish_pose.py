
import argparse
import pandas as pd
import sys

import rospy
import tf2_ros
import geometry_msgs.msg

from nav_msgs.msg import Odometry
from geometry_msgs.msg import Point, Pose, Quaternion, Twist, Vector3

def extract_timestamp(digits):
    assert len(digits) == 19, \
        f'The length of the digits is not 19. digits = {digits}. '
    
    return digits[:10], digits[10:]

def handle_args():
    parser = argparse.ArgumentParser(description='Publish a list of poses as RViz markers. ')

    parser.add_argument('--in_csv', type=str, required=True,
                        help='The CSV file that has all the poses. ')
    
    return parser.parse_args()

def main():
    # Handle the arguments.
    args = handle_args()
    
    rospy.init_node('csv_to_tf_publisher')
    tf_broadcaster = tf2_ros.TransformBroadcaster()
    
    odom_pub = rospy.Publisher("odom", Odometry, queue_size=10)
    
    # Read the CSV file.
    df = pd.read_csv(args.in_csv, header=0, dtype={'timestamp': 'str'})
    
    rate = rospy.Rate(50)
    
    for index, row in df.iterrows():
        # Get the sec and nsec.
        sec, nsec = extract_timestamp(row['timestamp'])
        
        timestamp = rospy.Time(secs=int(sec), nsecs=int(nsec))
        translation = (float(row['x']), float(row['y']), float(row['z']))
        rotation = (float(row['qx']), float(row['qy']), float(row['qz']), float(row['qw']))

        # tf_msg = geometry_msgs.msg.TransformStamped()
        # tf_msg.header.stamp = timestamp
        # tf_msg.header.frame_id = "world"
        # tf_msg.child_frame_id = "rig"
        # tf_msg.transform.translation.x = translation[0] - 188.27431170228132
        # tf_msg.transform.translation.y = translation[1] - (-139.24082646997755)
        # tf_msg.transform.translation.z = translation[2] - (-4.207249075320555)
        # tf_msg.transform.rotation.x = rotation[0]
        # tf_msg.transform.rotation.y = rotation[1]
        # tf_msg.transform.rotation.z = rotation[2]
        # tf_msg.transform.rotation.w = rotation[3]
        # tf_broadcaster.sendTransform(tf_msg)
        
        odom = Odometry()
        odom.header.stamp = timestamp
        odom.header.frame_id = "world"

        # set the position
        odom.pose.pose = Pose(
            Point( translation[0]- 188.27431170228132, 
                translation[1]- (-139.24082646997755), 
                translation[2]- (-4.207249075320555) ), 
            Quaternion(*rotation) )

        print(odom.pose.pose)

        # set the velocity
        odom.child_frame_id = "rig"
        odom.twist.twist = Twist(Vector3(0, 0, 0), Vector3(0, 0, 0))

        # publish the message
        odom_pub.publish(odom)
        
        rate.sleep()
    
    rospy.spin()
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
