#!/usr/bin/env python

import rospy
from std_msgs.msg import String
from nlu.msg import Command, Shape

import speech_recognition as sr
import requests
import numpy as np
import click
import json

INTENT_MAP = {'takeObject': Command.TAKE_OBJECT, 'putObject': Command.PUT_OBJECT}

RELATIVE_TO_MAP = {
  'in front of': Command.FRONT,
  'behind': Command.BEHIND,
  'on top of': Command.TOP,
  'on top': Command.TOP,
  'on the left': Command.LEFT,
  'on the right': Command.RIGHT,
}

@click.command()
@click.argument('remote', default='http://localhost:5078/intent')
def talker(remote):
    pub = rospy.Publisher('chatter', Command, queue_size=10)
    rospy.init_node('talker', anonymous=False)
    rate = rospy.Rate(1) # 10hz
    while not rospy.is_shutdown():
        output = raw_input('Type e to exit: ')
        if output.strip() == 'e':
            return
        sample_rate = 16000
        r = sr.Recognizer()
        with sr.Microphone(sample_rate=sample_rate) as source:
           print("Say Something")
           audio = r.listen(source)
           fs = audio.sample_rate
        audio = np.frombuffer(audio.frame_data, np.int16)
        print(audio)
        response = requests.post(remote, json={'payload': audio.tolist()})
        output = json.loads(response.content.decode(encoding='utf-8'))
        print(output)
        source_shape_slot = next((x for x in output['slots'] if x['slotName'] == 'shape'), None)
        source_shape_colour = next((x for x in output['slots'] if x['slotName'] == 'colour'), None)
        if source_shape_slot and source_shape_colour:
           source_block = Shape(source_shape_slot, source_shape_colour)
        else:
           rospy.loginfo("Source block not recognised!")
           continue

        relative_to_slot = next((x for x in output['slots'] if x['slotName'] == 'position'), None)
        if relative_to_slot:
           relative_to = RELATIVE_TO_MAP[relative_to_slot['value']['value']]
           target_shape_slot = next((x for x in output['slots'] if x['slotName'] == 'rel_pos_shape'), None)
           target_shape_colour = next((x for x in output['slots'] if x['slotName'] == 'rel_pos_colour'), None)
           if source_shape_slot and source_shape_colour:
             target_block = Shape(target_shape_slot, target_shape_colour)
           else:
             rospy.loginfo("Target block not recognised!")
             target_block = Shape("","")
        else:
           relative_to = Command.NONE
           rospy.loginfo("Relative position not recognised!")
           target_block = Shape("","")
        intent = INTENT_MAP.get(output['intent']['intentName'], None)
        if not intent:
           rospy.loginfo("Intent not recognised!")
           continue
        cmd = Command(intent, source_block, relative_to, target_block)

        rospy.loginfo(cmd)
        pub.publish(cmd)
    rate.sleep()

if __name__ == '__main__':
    try:
        talker()
    except rospy.ROSInterruptException:
        pass
