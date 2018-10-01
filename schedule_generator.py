# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import time

from PIL import Image, ImageDraw, ImageFont
import colorsys

import sys
import os

import random
import numpy as np

import itertools

# This program assumes no classes start on one day and end the next day!
# It also assumes that the night between Sunday and Monday will be a restful one, and ignores it.
# If a class has two different meeting times on two different days, this program will raise a flag. Not yet able to parse those.
# MAKE SURE that when you're comparing schedules, they're comparable! ie. similar number of credits

current_time = datetime.now().strftime('%Y-%m-%d %H-%M-%S')

INPUT = '_input csv.csv'
OUTPUT_DIR = '_output schedules ' + current_time

MIN_CREDITS = 16
MAX_CREDITS = 16

class Block:
    def __init__(self, date, start, end, course_code):
        self.date = date  # Monday is 1, Sunday is 7
        self.start = start
        self.end = end
        # print(day, start, end)
        self.duration = (end - start).seconds / 60
        self.course_code = course_code

    def __eq__(self, other):
        # if two blocks are "equal", then they're considered colliding = schedule conflict
        if self.date != other.date:
            return False
        else:
            if self.end >= other.start and self.end <= other.end:
                return True
            if self.start >= other.start and self.start <= other.end:
                return True
            return False

    def __str__(self):
        return self.start

    def __gt__(self, other):
        return self.start > other.start

class Section:
    def __init__(self, section_dict, credits, course_code, course_name):
        self.section = section_dict['Section']
        self.days_and_times = section_dict['Days and times']

        # self.credits = 0  # I don't think this is necessary to store here. Credits is used only in generating the combinations.
        self.credits = credits
        self.course_code = course_code
        self.course_name = course_name

        self.blocks = []
        # print(section_dict)
        
        # 'MoWeTh 12:10PM - 1:00PM'
        # ? how to handle strings with different times on different days?
        split = section_dict['Days and times'].split(' ')
        assert len(split) == 4, "We have a class with a nonstandard 'Days and times' string format! " + section_dict
        for n in range(int(len(split[0]) / 2)): # for weekdays in the weekdays string
            # the month date needs to start on a 1, and it happens to be a Monday in January of 1900
            date = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'].index(split[0][n * 2:(n + 1)*2]) + 1
            # Be careful! All these datetime objects have the same default year and month! Dates are 1 for Monday and 6 for Saturday.
            start = datetime.strptime(str(date) + ' ' + split[1], '%d %I:%M%p')
            end   = datetime.strptime(str(date) + ' ' + split[3], '%d %I:%M%p')
            # print(datetime.strftime(start, '%d %w %I:%M%p %Y-%m-%d'))
            assert end > start, "\nThe end time is before the start time! " + datetime.strftime(start, '%H:%M') + ' ' + datetime.strftime(end, '%H:%M')
            self.blocks.append(Block(date, start, end, self.course_code))

    def __eq__(self, other):    # if the section collides with another section, return True
        for block1 in self.blocks:
            for block2 in other.blocks:
                if block1 == block2:
                    return True
        return False

    def __str__(self):
        return self.course_code + ' ' + self.course_name + ' ' + self.section
            
class Coreq:
    def __init__(self, sections_list):
        self.course_code = sections_list[0]['Course code']
        self.course_name = sections_list[0]['Course name']
        self.credits = float(sections_list[0]['Credits'])
        self.sections = []
        
        for section in sections_list:
            self.sections.append(Section(section, self.credits, self.course_code, self.course_name))

    def __str__(self):
        return self.course_code + ' ' + self.course_name

class Course:
    def __init__(self, dicts_list):
        self.required = False
        self.coreqs = []
        self.total_credits = 0
        if dicts_list[0]['Required?'] == 'r':
            self.required = True

        course_code = ''
        temp = []
        for dict in dicts_list:
            if dict['Course code'] != course_code:
                course_code = dict['Course code']
                temp.append([dict])
            else:
                temp[-1].append(dict)
        for list in temp:
            self.coreqs.append(Coreq(list))
            self.total_credits += float(list[0]['Credits'])

    def __str__(self):
        return self.coreqs[0].course_code + ' ' + self.coreqs[0].course_name

class ScheduleGenerator:
    def __init__(self, input_dicts):
        self.required = []  # list of lists of course codes and credits, grouped as corequisites
        self.flexible = []  # same as above

        temp = []
        for dict in input_dicts:
            if dict['Corequisites?'] == 'c':
                temp.append([dict])
            else:
                temp[-1].append(dict)
        for list in temp:
            if list[0]['Required?'] == 'r':
                self.required.append(Course(list))
            else:
                self.flexible.append(Course(list))

    def generate_schedules(self):
        self.schedules = []

        for n in range(0, len(self.flexible) + 1):  # n elements -> n+1 possible sizes of subsets, 0 to n
            for element in list(itertools.combinations(self.flexible, n)):
                combination = list(element) + self.required # a list of Course objects
                combination = [f.coreqs for f in combination]   # a list of lists of Coreq objects
                combination = list(itertools.chain.from_iterable(combination))  # a list of Coreq objects
                credits = sum([f.credits for f in combination])

                # only consider combinations that fulfill the required number of credits
                if credits >= MIN_CREDITS and credits <= MAX_CREDITS:
                    combination = [f.sections for f in combination] # a list of lists of Section objects

                    # schedule is any possible combination of sections
                    for possible_schedule in list(itertools.product(*combination)):
                        self.schedules.append(Schedule(possible_schedule))
                        self.schedules[-1].credits = credits

        # eliminate any combinations of courses that contain a conflict
        self.schedules = [f for f in self.schedules if f.contains_conflict() == False]

        # calculate the properties of each schedule
        for schedule in self.schedules:
            schedule.calculate()

        # eliminate any schedule that contains a Saturday class
        self.schedules = [f for f in self.schedules if f.saturday_class == False]
        # wouldn't it just be faster to ignore any "Date and time" strings containing an "Sa"?

        # we can filter out schedules with classes before 9 AM or classes after 6 PM here
        no_mornings = [f for f in self.schedules if f.early_morns == 0]
        # print(len(no_mornings))
        no_nights = [f for f in self.schedules if f.late_nights == 0]
        # print(len(no_nights))

        # filter out schedules with a night class immediately followed by an early morning class
        self.schedules = [f for f in self.schedules if f.sleepless == 0]
        # print(len(self.schedules))

        # rank the remaining schedules by how clustered the classes are
        self.schedules.sort(key=lambda x: x.class_time / x.total_time, reverse=True)  # pretty good results, though classes can end up being late at night

        # the following are alternative ways of ranking the remaining schedules, each with a slightly different result
        # self.schedules.sort(key=lambda x: x.total_time, reverse=False)    # will simply prefer fewer credits
        # self.schedules.sort(key=lambda x: x.credits, reverse=False)   # we should just make the credits range narrower
        # self.schedules.sort(key=lambda x: x.weight * x.class_time / x.total_time, reverse=True) # pulls classes toward 1PM at the expense of more breaks between classes, days with a single class, and lower overall fullness
        # try adding 1.5 hours as travel time after 8 PM? 2 hours after 10? travel time as a function of time of day? may also need to account for direction of travel: 80 minutes vs. 40 minutes, days that end early or start late.
        # self.schedules.sort(key=lambda x: x.class_time / x.total_time / credits, reverse=True)    # try to scale fullness with credits, since more credits tends to lower fullness


        # print out the fullness and credit load of the top 10 and bottom 10 ranked schedules, for comparison
        """
        for schedule in self.schedules[:10]:
            print(str(round(schedule.total_time / 60, 2)) + '\t' + str(round(schedule.class_time / schedule.total_time, 4)) + '\t' + str(schedule.credits) + '\t' + str(schedule.total_time) + '\t' + str(schedule.class_time) + '\t' + str(schedule.travel_time))
        print('\n\n')
        for schedule in self.schedules[-10:]:
            print(str(round(schedule.total_time / 60, 2)) + '\t' + str(round(schedule.class_time / schedule.total_time, 4)) + '\t' + str(schedule.credits))
        """
        
        
        # the following code saves to images schedules that are different
            # for when you have two sections of the same class at the same time
            # to prevent what can be considered as "identical" schedules to both be saved to images
            # the skipped numbers will indicate if you have more than one section for a particular time
        already_printed = []
        x = 0
        while len(already_printed) < 10 and x < len(self.schedules):
            match = False
            for schedule in already_printed:
                if self.schedules[x] == schedule:
                    match = True
            if match == False:
                already_printed.append(self.schedules[x])
                self.schedules[x].save_image('preferred ' + str(x).zfill(2))
            x += 1

        already_printed = []
        x = 0
        while len(already_printed) < 10 and x < len(self.schedules):
            match = False
            for schedule in already_printed:
                if self.schedules[-x -1] == schedule:
                    match = True
            if match == False:
                already_printed.append(self.schedules[-x -1])
                self.schedules[-x -1].save_image('undesirable ' + str(x + 1).zfill(2))
            x += 1

class Schedule:
    def __init__(self, sections_list):
        self.sections = sections_list   # list of Section objects
        self.credits = 0

        self.early_morns = 0
        self.late_nights = 0
        self.sleepless = 0

        self.saturday_class = False

        self.total_time = 0
        self.travel_time = 0
        self.class_time = 0

        # weight = sum of ((gaussian(start) + gaussian(end)) / 2) * duration
        self.weight = 0

    def __str__(self):
        return '\n'.join([f.course_code + ' ' + f.course_name + ' ' + f.section for f in self.sections])

    def __eq__(self, other):
        self_blocks = [f.blocks for f in self.sections]
        self_blocks = list(itertools.chain.from_iterable(self_blocks))  # a list of block
        other_blocks = [f.blocks for f in other.sections]
        other_blocks = list(itertools.chain.from_iterable(other_blocks))
        sched_match = True
        for block1 in self_blocks:
            block_match = False
            for block2 in other_blocks:
                if block1.course_code == block2.course_code and block1.start == block2.start and block1.end == block2.end:
                    block_match = True
            if block_match == False:
                sched_match = False
        return sched_match

    def contains_conflict(self):
        '''Returns true if the schedule contains at least one collision/conflict.'''
        for section1 in self.sections:
            for section2 in self.sections:
                if section1.course_code != section2.course_code:
                    if section1 == section2:
                        return True
        return False

    def gaussian(self, datetime):
        # 8 AM to 1 PM to 6 PM
        # bug: will favor schedules with more overall credits/classes, so normalize to total duration of classes?
        minutes = (datetime - datetime.strptime('8:00AM', '%I:%M%p')).seconds / 60 # minutes past 8:00
        # print(minutes)
        mu = 0
        sig = 1
        x = -3 + (minutes / 600) * 6
        return np.exp(-np.power(x - mu, 2.) / (2 * np.power(sig, 2.))) - 0.25

    def calculate(self):
        '''Update the attributes pertaining to the schedule.'''
        days = [[], [], [], [], [], [], []] # Monday (date 1) is the first, at index 0
        blocks = [f.blocks for f in self.sections]
        blocks = list(itertools.chain.from_iterable(blocks))    # a list of all blocks
        blocks.sort()
        for block in blocks:
            days[block.date - 1].append(block)
        if days[6 - 1] != []: # Saturday is non-empty
            self.saturday_class = True
        for day in days:
            if day != []:
                self.travel_time += 2 * 60
                self.total_time += 2 * 60
                for block in day:
                    self.class_time += block.duration
                    self.total_time += block.duration
                for n in range(0, len(day) - 1):
                    break_length = (day[n + 1].start - day[n].end).seconds / 60    # convert timedelta to minutes
                    self.total_time += break_length

        early_morn = [False, False, False, False, False, False, False]
        late_night = [False, False, False, False, False, False, False]
        for n, day in enumerate(days):
            start = datetime.strptime(str(n + 1) + ' ' + '12:00AM', '%d %I:%M%p')
            end   = datetime.strptime(str(n + 1) + ' ' + '09:00AM', '%d %I:%M%p')
            morning = Block(n + 1, start, end, '')
            start = datetime.strptime(str(n + 1) + ' ' + '05:00PM', '%d %I:%M%p')
            end   = datetime.strptime(str(n + 1) + ' ' + '11:59PM', '%d %I:%M%p')
            night = Block(n + 1, start, end, '')
            for block in day:
                if block == morning:
                    early_morn[n] = True
                if block == night:
                    late_night[n] = True
        self.early_morns = early_morn.count(True)
        self.late_nights = late_night.count(True)
        for n, day in enumerate(days[:-1]):
            if late_night[n] == True and early_morn[n + 1] == True:
                self.sleepless += 1

        for block in blocks:
            self.weight += ((self.gaussian(block.start) + self.gaussian(block.end)) / 2) * block.duration / 60

    def datetime_to_coords(self, string):
        '''Given a string of form 'MoTh 8:10AM - 9:25AM'
        return a list of coords of form (x1, y1, x2, y2) for outputting to PNG.'''
        split = string.split(' ')
        output_list = []
        for n in range(int(len(split[0]) / 2)): # for weekdays in the weekdays string
            decimal_day = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'].index(split[0][n * 2:(n + 1)*2])
            assert decimal_day <= 4, 'No Saturdays or Sundays allowed!'
            x1 = int(150 * (0.875 + decimal_day * (1.375)))
            x2 = int(150 * (0.875 + decimal_day * (1.375) + 1.25))
            start = datetime.strptime(split[1], '%I' + ':' + '%M' + '%p')
            end = datetime.strptime(split[3], '%I' + ':' + '%M' + '%p')
            assert start < end, 'start time is later than end time!'

            y1 = 104 + 10 * ((int(datetime.strftime(start, '%H')) - 8) * 12 + round((int(datetime.strftime(start, '%M')) / 5)))
            y2 = 104 + 10 * ((int(datetime.strftime(end, '%H')) - 8) * 12 + round((int(datetime.strftime(end, '%M')) / 5)))
            output_list.append((x1, int(y1), x2, int(y2)))
        return output_list

    def save_image(self, filename):   # sections_dicts, image_filename
        output_dir = OUTPUT_DIR
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)
        image_filename = filename

        font = ImageFont.truetype("calibri.ttf", 19)
        font_color = (0, 0, 0)

        new_image = Image.new('RGB', (int(8.5 * 150), 11 * 150))
        draw = ImageDraw.Draw(new_image)
        draw.rectangle((0, 0, int(8.5 * 150), 11 * 150), (255, 255, 255, 255))        

        # write the hours
        for x in range(8, 20):
            hour = x % 12
            if hour == 0:
                hour = 12
            hour = str(hour)
            if int(x / 12) == 1:
                ampm = 'PM'
            else:
                ampm = 'AM'
            string = hour + ':00 ' + ampm
            draw.text((int(0.25 * 150), int(((x - 8) * 120) + 0.25 * 150 + 67)), string, font_color, font=font)
            draw.text((int((8.5 - 0.25 - 0.5) * 150), int(((x - 8) * 120) + 0.25 * 150 + 67)), string, font_color, font=font)

        # draw the major and minor hour lines
        for x in range(8, 21):
            draw.line((0, int((x - 8) * 120 + 0.25 * 150 + 67), int(8.5 * 150), int((x - 8) * 120 + 0.25 * 150 + 67)), fill=(128, 128, 128), width=3)
        for x in range(8, 20):
            draw.line((0, int((x - 8) * 120 + 0.25 * 150 + 67 + 60), int(8.5 * 150), int((x - 8) * 120 + 0.25 * 150 + 67 + 60)), fill=(192, 192, 192), width=3)

        # coloring the columns for the days
        for x in range(5):
            x1 = int(150 * (0.25 + 0.5 + 0.125 + x * (0.125 + 1.25)))
            y1 = int(150 * (0.25) + 67)
            x2 = int(150 * (0.25 + 0.5 + 0.125 + x * (0.125 + 1.25) + 1.25))
            y2 = int(150 * (11 - 0.25) - 67)
            drw = ImageDraw.Draw(new_image, 'RGBA')
            drw.rectangle((int(150 * (0.25 + 0.5 + 0.125 + x * (0.125 + 1.25))), int(150 * (0.25) + 67), int(150 * (0.25 + 0.5 + 0.125 + x * (0.125 + 1.25) + 1.25)), int(150 * (11 - 0.25) - 67)), (random.randint(63, 191), random.randint(63, 191), random.randint(63, 191), 16))
        del drw

        # write in the days
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        for x in range(5):
            spaces = ' ' * (21 - len(days[x]))
            draw.text((int(150 * (0.25 + 0.5 + 0.125 + x * (0.125 + 1.25))), int(150 * (0.25) + 67 - 20)), spaces + days[x], font_color, font=font)

        # generate a semi-random palette of colors
        colors = []
        shift = random.randint(0, 999) / 1000
        for x in range(int(len(self.sections) * 2)):
            h = x / int((len(self.sections) * 2))
            r, g, b = colorsys.hsv_to_rgb((h + shift) % 1, 0.3, 1.0)
            colors.append((round(255 * r), round(255 * g), round(255 * b)))

        # write course information onto each box in the output image
        indent = 4
        line_length = 21
        for n, section in enumerate(self.sections):
            input_strings = [section.course_code, section.section, section.course_name, section.days_and_times[section.days_and_times.index(' ') + 1:]]
            printing_strings = []
            for string in input_strings:
                head = string[:indent]
                string = string[indent:]
                for x in range(int(len(string) / (line_length - indent)) + 1):
                    if x == 0:
                        printing_strings.append(head + string[x * (line_length - indent) : (x + 1) * (line_length - indent)])
                    else:
                        printing_strings.append(' ' * indent + string[x * (line_length - indent) : (x + 1) * (line_length - indent)])

            color = colors[n]
            for block in self.datetime_to_coords(section.days_and_times):
                draw.rectangle(block, color)
                for m, string in enumerate(printing_strings):
                    draw.text((block[0] + 3, block[1] + 2 + (m * 20)), string, font_color, font=font)

        del draw

        new_image.save(os.path.join(output_dir, image_filename + '.png'), 'PNG')

def read_csv(path):
    '''Given the path to the default input CSV,
    return a list of all the sections and the classes they belong to.
    Labels are on the first row of the CSV.
    Make sure the fields are delimited by tabs, and the fields are enclosed by quotes, especially the numbers.'''
    with open(path, 'r', encoding='utf-8') as input_file:
        input_lines = [f.strip(' \n') for f in input_file.readlines()]
        # Don't strip \t here!! They're needed for blank cells.
    output_lines = []
    labels = input_lines[0].replace('"', '').split('\t')
    for n, element in enumerate(input_lines[1:]):
        temp = element.replace('"', '').split('\t')
        line_dict = {}
        for m, label in enumerate(labels):
            line_dict[label] = temp[m]
        output_lines.append(line_dict)
    return output_lines


# read in data from the CSV
input_lines = read_csv(INPUT)
# place the data into the nested classes structure
fall_2018 = ScheduleGenerator(input_lines)
# generate, filter, and rank possible schedules
fall_2018.generate_schedules()
