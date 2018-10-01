# Schedule Generator

This program is to be used by a student to generate plausible schedules from the course catalog.

Normally, the student needs to manually create schedules by examining the section times and plotting them onto paper or software. This task can be time-consuming and tedious for a human to complete, but the mechanical nature of the task also means it can be easily automated.

The purpose of this program isn't necessarily to create the best possible schedule given a selection of courses, but it frees the student to focus on more important decisions. The program generates all possible schedules, eliminates schedules based on certain conditions, and ranks the remaining schedules based on how closely clustered the classes are. The higher ranked schedules are saved as images so that the student can see at a glance what kinds of schedules are possible.

## Prerequisites

In addition to the Python Standard Library, this program requires numpy and the Python Image Library (PIL) packages to work.

## Usage:

The program takes an _input csv.csv containing information about courses from the catalog. A sample showing how the CSV should be formatted is included. The program may be run with the provided sample.

The way courses are grouped together as corequisites in the course catalog is inconsistent, so the student needs to manually indicate which courses and sections are to be registered as a group. This is done by placing a "c" in the "Corequisites?" column.

In addition to information about each section's days and times and credit load, the student needs to indicate which courses are required for the semester and which are flexible. "Required" means that the course must be contained in the output schedules, while "flexible" means that the course may or may not be included in order to fulfill the credit requirements. Courses that are prerequisites to further courses are usually the ones marked as "required", for the student to not fall behind schedule towards completing their degree.

It is important that the days and times are formatted exactly as they are in the sample, or else the program won't be able to understand them.

```
MoTh 8:10AM - 9:25AM
```

It is also important that each section possesses a unique Section number.

Once the CSV is filled out and properly formatted, the program can be run. The generated schedules should be found in the newly created output folder.

## How the program behaves and why:

The program looks at all possible subsets of the "flexible" courses and combines them with the "required" courses to produce combinations of courses. The program ignores any combination of courses that does not fulfill the credit requirement.

It then looks at the sections in those courses, and creates every possible combination of sections. A combination of sections will henceforth be referred to as a "schedule." The program eliminates any schedules containing a collision, i.e. two sections occurring at the same time.

With plausible schedules remaining, the program can optionally eliminate any schedules containing a "sleepless" night, which is a night class followed immediately by an early morning class the next day. The same thing can be done for classes before 9 AM and classes after 6 PM.

The remaining schedules are ranked by how closely clustered the classes are. More compact schedules are favored over schedules containing three or five hour breaks between classes. This step also favors schedules with classes contained to fewer days.

With the schedules ranked, the program finally outputs the top ten and bottom ten schedules as PNG images into the output folder. It is important that the outputs be images rather than lines of text, as they're easier for the student to understand at a glance.

## To do:

Allow the student to specify blocks of time to keep free for other commitments.

A utility to automatically generate a properly formatted CSV from only selections copied and pasted from the course catalog web pages.

A GUI so students don't need to type letters into a spreadsheet in order to communicate with the program. It would make it easier for them to customize options to suit their own needs.

Increase travel time to 2 hours for classes that end after 8 PM. Define a smooth function to control this. Hopefully this will penalize schedules with too many night classes.
