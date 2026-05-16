# mediageoplot
An app that scans media files for geolocations and shows these locations on a map.

## What is this?
Media files (photo, video) often contain geolocations in their metadata. This app scans one or more directories with media files, checks their metadata and gets geolocations if they are available. It then plots them on a map. You can open the map in a browser. Also, a html file is saved in the first directory.

## How was this made?
The original was a Python program I made that you had to run on the command line. I've asked Claude Code to make this into a GUI.

## What files will it scan for geolocations?
Photo: JPG and HEIC
Video: MP4, sidecars (.XML) and AVCHD (.MTS).
(Often the video files don't have the geolocation in their general metadata, but it's in their frames. This app uses the first geolocation it find.)
